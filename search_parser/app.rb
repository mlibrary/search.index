require "sinatra/base"
require "sinatra/namespace"
require "puma"
require "mlibrary_search_parser"
require "yaml"
require "active_support"
require "active_support/core_ext/hash/indifferent_access"
require_relative "lib/services"
require_relative "lib/metrics"
require "debug" if S.app_env == "development"

Metrics::Yabeda.configure!

class SearchParser
  def self.facets
    @facets ||= self::CONFIG["facets"].freeze
  end

  def self.builder
    @builder ||= MLibrarySearchParser::SearchBuilder.new(self::CONFIG)
  end

  def self.build(query)
    builder.build(query)
  end

  def self.facet_params
    result = {}

    facets.each do |field|
      result["f.#{field}.facet.limit"] = "50"
      result["f.#{field}.facet.mincount"] = "1"
      result["f.#{field}.facet.offset"] = "0"
      result["f.#{field}.facet.sort"] = "count"
    end
    result["facet.field"] = facets
    result["fl"] = "*,score"
    result["facet"] = true

    result
  end

  # copied from: https://github.com/rsolr/rsolr/blob/a60ec42b58f3b068f23537e49d0b6510bb12ee17/lib/rsolr.rb#L25
  # backslash escape characters that have special meaning to Solr query parser
  # per http://lucene.apache.org/core/4_0_0/queryparser/org/apache/lucene/queryparser/classic/package-summary.html#Escaping_Special_Characters
  #  + - & | ! ( ) { } [ ] ^ " ~ * ? : \ /
  # see also http://svn.apache.org/repos/asf/lucene/dev/tags/lucene_solr_4_9_1/solr/solrj/src/java/org/apache/solr/client/solrj/util/ClientUtils.java
  #   escapeQueryChars method
  # @return [String] str with special chars preceded by a backslash
  def self.solr_escape(str)
    # note that the gsub will parse the escaped backslashes, as will the ruby code sending the query to Solr
    # so the result sent to Solr is ultimately a single backslash in front of the particular character
    str.gsub(/([+\-&|!(){}\[\]\^"~*?:\\\/])/, '\\\\\1')
  end

  def self.datastore
    name.to_s.split("::").last.downcase
  end

  def self.solr_query(query:, rows:, start:, sort:, fq:)
    # how to handle fq:
    # fq":["topicStr:(Motion\\ pictures)","institution:(UM\\ Ann\\ Arbor\\ Libraries)","+(new_availability:physical OR new_availability:hathi_trust_full_text_or_electronic_holding)"]
    # sort comes from config/sorts.yml
    lp = MLibrarySearchParser::Transformer::Solr::LocalParams.new(build(query))

    result = {
      rows: rows,
      start: start,
      sort: sort,
      fq: fq
    }.merge(facet_params).merge(lp.params).with_indifferent_access

    result["qt"] = "standard" unless ["edismax", "dismax"].include?(result["qt"]) # code from spectrum so I don't forget. Don't know if we need this.
    result["qq"] = '"' + solr_escape(result["q"]) + '"'
    S.logger.info("results_query", datastore: datastore, query: result)
    result
  end

  def self.academic_discipline_solr_query(query:, fq:)
    # how to handle fq:
    # fq":["topicStr:(Motion\\ pictures)","institution:(UM\\ Ann\\ Arbor\\ Libraries)","+(new_availability:physical OR new_availability:hathi_trust_full_text_or_electronic_holding)"]
    # sort comes from config/sorts.yml
    lp = MLibrarySearchParser::Transformer::Solr::LocalParams.new(build(query))

    result = {
      rows: 100,
      start: 0,
      sort: "score desc",
      fq: fq,
      fl: "hlb3Str"
    }.merge(lp.params).with_indifferent_access
    S.logger.info("academic_disciplines_query", datastore: datastore, query: result)
    result
  end

  class Catalog < self
    CONFIG = YAML.safe_load_file("./config/catalog.yaml", aliases: true).freeze
  end

  class Onlinejournals < self
    CONFIG = YAML.safe_load_file("./config/onlinejournals.yaml", aliases: true).freeze
  end

  class Articles < self
    CONFIG = YAML.safe_load_file("./config/articles.yaml", aliases: true).freeze

    def self.primo_fields
      @facets ||= self::CONFIG["primo_fields"].freeze
    end

    def self.primo_query(params)
      results = {
        q: primo_q(params[:q]),
        sort: params[:sort],
        offset: params[:offset],
        limit: params[:limit],
        scope: "CentralIndex",
        tab: "CentralIndex",
        vid: "01UMICH_INST:UMICH",
        disableSplitFacets: "true"
      }
      [:qInclude, :qExclude, :pcAvailability].each do |field|
        results[field] = params[field] if params[field]
      end
      results
    end

    def self.primo_q(query)
      tree = build(query)
      tree.children.map do |child|
        parse_node(node: child)
      end.join(",AND;")
        .gsub(/,(AND|OR);,NOT;/, ",NOT;")
        .gsub(/^,NOT;/, "any,contains,*,NOT;")
    end

    def self.parse_node(node:, field: "any", precision: "contains")
      case node.node_type
      when :tokens
        [field, precision, node.text].join(",")
      when :fielded
        mapped_field = primo_fields[node.field]
        parse_node(node: node.query, field: mapped_field["field"], precision: mapped_field["precision"])
      when :and
        node.children.map do |child|
          parse_node(node: child)
        end.join(",AND;")
      when :or
        if node_has_fielded_children?(node)
          node.children.map do |child|
            parse_node(node: child)
          end.join(",OR;")
        else
          joined_keywords = node.children.map do |child|
            extract_keywords(child)
          end.join(" OR ")
          [field, precision, "(#{joined_keywords})"].join(",")
        end
      when :not
        result = node.children.map do |child|
          parse_node(node: child)
        end.join(",NOT;")
        ",NOT;" + result
      end
    end

    def self.extract_keywords(node)
      if node.is_type?(:tokens)
        node.text
      elsif [:and, :or, :not].any? { |type| node.is_type?(type) }
        "(" + node.children.map { |child| extract_keywords(child) }.join(" #{node.operator.to_s.upcase} ") + ")"
      end
    end

    def self.node_has_fielded_children?(node)
      return true if node.is_type?(:fielded)
      return false if node.is_type?(:tokens)
      node.children.any? { |child| node_has_fielded_children?(child) }
    end
  end
end

class SearchParser::Application < Sinatra::Base
  register Sinatra::Namespace
  set :host_authorization, {permitted_hosts: []}
  namespace "/catalog" do
    get "/search" do
      headers "metrics.route" => "catalog/search"
      content_type :json
      query_params = {
        query: params["query"] || "",
        rows: params["rows"] || 10,
        start: params["start"] || 0,
        sort: params["sort"] || "score desc",
        fq: params["fq"] || ["institution:(UM\\ Ann\\ Arbor\\ Libraries)", "+(availability:physical OR availability:hathi_trust_full_text_or_electronic_holding)"]
      }
      #      response = nil
      solr_params = SearchParser::Catalog.solr_query(**query_params)
      #      Yabeda.catalog_solr_query_duration.measure do
      response = S.solr_conn.get("solr/#{S.solr_core}/select", solr_params)
      #      end
      response.body.to_json
    end

    get "/academic_disciplines" do
      headers "metrics.route" => "catalog/academic_disciplines"
      content_type :json
      query_params = {
        query: params["query"] || "",
        fq: params["fq"] || ["institution:(UM\\ Ann\\ Arbor\\ Libraries)", "+(availability:physical OR availability:hathi_trust_full_text_or_electronic_holding)"]
      }
      solr_params = SearchParser::Catalog.academic_discipline_solr_query(**query_params)

      response = S.solr_conn.get("solr/#{S.solr_core}/select", solr_params)

      response.body.to_json
    end
  end
  namespace "/onlinejournals" do
    get "/search" do
      headers "metrics.route" => "onlinejournals/search"
      content_type :json
      query_params = {
        query: params["query"] || "",
        rows: params["rows"] || 10,
        start: params["start"] || 0,
        sort: params["sort"] || "score desc",
        fq: params["fq"] || []
      }

      query_params[:fq].push("location:ELEC")
      query_params[:fq].push("format:Serial")
      #      response = nil
      solr_params = SearchParser::Onlinejournals.solr_query(**query_params)
      #      Yabeda.catalog_solr_query_duration.measure do
      response = S.solr_conn.get("solr/#{S.solr_core}/select", solr_params)
      #      end
      response.body.to_json
    end

    get "/academic_disciplines" do
      headers "metrics.route" => "onlinejournals/academic_disciplines"
      content_type :json
      query_params = {
        query: params["query"] || "",
        fq: params["fq"] || []
      }
      query_params[:fq].push("location:ELEC")
      query_params[:fq].push("format:Serial")
      solr_params = SearchParser::Onlinejournals.academic_discipline_solr_query(**query_params)

      response = S.solr_conn.get("solr/#{S.solr_core}/select", solr_params)

      response.body.to_json
    end

    get "/browse_academic_discipline/:academic_discipline" do |academic_discipline|
      headers "metrics.route" => "onlinejournals/browse_academic_discipline"

      content_type :json
      query_params = {
        query: "",
        rows: params["rows"] || 10,
        start: params["start"] || 0,
        fq: []
      }
      query_params[:fq].push("location:ELEC")
      query_params[:fq].push("format:Serial")
      query_params[:fq].push("hlb3Str:\"#{academic_discipline}\"")
      bb_field = "#{academic_discipline.downcase.gsub(/\s+/, "_")}_bb"

      query_params[:sort] = "#{bb_field} asc,titleSort asc"
      solr_params = SearchParser::Onlinejournals.solr_query(**query_params)

      response = S.solr_conn.get("solr/#{S.solr_core}/select", solr_params)

      response.body.to_json
    end
  end
  namespace "/articles" do
    get "/search" do
      headers "metrics.route" => "articles/search"
      content_type :json
      query_params = {
        q: params["q"] || "",
        sort: params[:sort] || "rank",
        offset: params[:offset] || 0,
        limit: params[:limit] || 10
      }
      [:qInclude, :qExclude, :pcAvailability].each do |field|
        query_params[field] = params[field.to_s] if params[field.to_s]
      end
      S.logger.info("primo_params", **query_params)
      conn = Faraday.new(
        headers: {"Content-Type" => "application/json",
                  "Accept" => "application/json",
                  "Authorization" => "apikey #{S.primo_api_key}"}
      ) do |f|
        f.request :json
        f.response :json
      end

      response = conn.get("https://api-na.hosted.exlibrisgroup.com/primo/v1/search", SearchParser::Articles.primo_query(query_params))
      S.logger.info("primo_request", url: response.url.to_str)
      response.body.to_json
    end
  end
end
