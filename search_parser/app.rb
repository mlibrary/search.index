require "sinatra/base"
require "sinatra/namespace"
require "puma"
require "mlibrary_search_parser"
require "yaml"
require "active_support"
require "active_support/core_ext/hash/indifferent_access"
require_relative "lib/services"
require_relative "lib/metrics"
require_relative "lib/mlibrary_search_parser_transformer_sometimes_quoted_local_params"
require_relative "lib/datastore"
require "debug" if S.app_env == "development"

Metrics::Yabeda.configure!

module SearchParser
  DATASTORES = {
    catalog: SearchParser::Datastore::Solr.for("./config/catalog.yaml"),
    onlinejournals: SearchParser::Datastore::Solr.for("./config/onlinejournals.yaml"),
    databases: SearchParser::Datastore::Solr.for("./config/databases.yaml"),
    articles: SearchParser::Datastore::Primo.for("./config/articles.yaml")
  }

  def self.get_datastore(datastore)
    self::DATASTORES[datastore]
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
      solr_params = SearchParser.get_datastore(:catalog).solr_query(**query_params)

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
      solr_params = SearchParser.get_datastore(:catalog).academic_discipline_solr_query(**query_params)

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
      solr_params = SearchParser.get_datastore(:onlinejournals).solr_query(**query_params)
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
      solr_params = SearchParser.get_datastore(:onlinejournals).academic_discipline_solr_query(**query_params)

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
      solr_params = SearchParser.get_datastore(:onlinejournals).solr_query(**query_params)

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

      response = conn.get("https://api-na.hosted.exlibrisgroup.com/primo/v1/search", SearchParser.get_datastore(:articles).primo_query(query_params))
      S.logger.info("primo_request", url: response.url.to_str)
      response.body.to_json
    end
  end
  namespace "/databases" do
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
      query_params[:fq].push("type:database")

      datastore = SearchParser.get_datastore(:databases)
      solr_params = datastore.solr_query(**query_params)
      #      Yabeda.catalog_solr_query_duration.measure do
      response = S.website_solr_conn.get("solr/#{S.website_solr_core}/select", solr_params)
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
      query_params[:fq].push("type:database")
      datastore = SearchParser.get_datastore(:databases)
      solr_params = datastore.academic_discipline_solr_query(**query_params)

      response = S.website_solr_conn.get("solr/#{S.website_solr_core}/select", solr_params)

      response.body.to_json
    end
  end
end
