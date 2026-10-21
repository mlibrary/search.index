module SearchParser
  class Datastore
    def self.for(config_file_path)
      config_data = YAML.safe_load_file(config_file_path, aliases: true).freeze
      new(config_data)
    end
    attr_reader :config
    def initialize(config)
      @config = config
    end

    def name
      config["name"]
    end

    def builder
      @builder ||= MLibrarySearchParser::SearchBuilder.new(config)
    end

    def build(query)
      builder.build(query)
    end

    def get_local_params(query)
      Object.const_get(config["transformer"]).new(build(query))
    end

    class Solr < self
      def facets
        @facets ||= config["facets"].freeze
      end

      def search(params)
        solr_name = config["solr_name"]
        solr_core = "#{solr_name}_solr_core"
        S["#{solr_name}_solr_conn"].get("solr/#{S[solr_core]}/select", params)
      end

      def facet_params
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

      def solr_query(query:, rows:, start:, sort:, fq:)
        # how to handle fq:
        # fq":["topicStr:(Motion\\ pictures)","institution:(UM\\ Ann\\ Arbor\\ Libraries)","+(new_availability:physical OR new_availability:hathi_trust_full_text_or_electronic_holding)"]
        # sort comes from config/sorts.yml
        lp = get_local_params(query)

        result = {
          rows: rows,
          start: start,
          sort: sort,
          fq: fq
        }.merge(facet_params).merge(lp.params).with_indifferent_access

        result["qt"] = "standard" unless ["edismax", "dismax"].include?(result["qt"]) # code from spectrum so I don't forget. Don't know if we need this.
        result["qq"] = '"' + solr_escape(result["q"]) + '"'
        result["wt"] = "json"
        S.logger.info("results_query", datastore: name, query: result)
        result
      end

      def academic_discipline_solr_query(query:, fq:)
        lp = get_local_params(query)

        result = {
          rows: 100,
          start: 0,
          sort: "score desc",
          fq: fq,
          fl: config["academic_discipline_field"]
        }.merge(lp.params).with_indifferent_access
        result["wt"] = "json"
        S.logger.info("academic_disciplines_query", datastore: name, query: result)
        result
      end

      private

      # copied from: https://github.com/rsolr/rsolr/blob/a60ec42b58f3b068f23537e49d0b6510bb12ee17/lib/rsolr.rb#L25
      # backslash escape characters that have special meaning to Solr query parser
      # per http://lucene.apache.org/core/4_0_0/queryparser/org/apache/lucene/queryparser/classic/package-summary.html#Escaping_Special_Characters
      #  + - & | ! ( ) { } [ ] ^ " ~ * ? : \ /
      # see also http://svn.apache.org/repos/asf/lucene/dev/tags/lucene_solr_4_9_1/solr/solrj/src/java/org/apache/solr/client/solrj/util/ClientUtils.java
      #   escapeQueryChars method
      # @return [String] str with special chars preceded by a backslash
      def solr_escape(str)
        # note that the gsub will parse the escaped backslashes, as will the ruby code sending the query to Solr
        # so the result sent to Solr is ultimately a single backslash in front of the particular character
        str.gsub(/([+\-&|!(){}\[\]\^"~*?:\\\/])/, '\\\\\1')
      end
    end

    class Primo < self
      def primo_fields
        @primo_fields ||= config["primo_fields"].freeze
      end

      def primo_query(params)
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

      def primo_q(query)
        tree = build(query)
        tree.children.map do |child|
          parse_node(node: child)
        end.join(",AND;")
          .gsub(/,(AND|OR);,NOT;/, ",NOT;")
          .gsub(/^,NOT;/, "any,contains,*,NOT;")
      end

      def parse_node(node:, field: "any", precision: "contains")
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

      def extract_keywords(node)
        if node.is_type?(:tokens)
          node.text
        elsif [:and, :or, :not].any? { |type| node.is_type?(type) }
          "(" + node.children.map { |child| extract_keywords(child) }.join(" #{node.operator.to_s.upcase} ") + ")"
        end
      end

      def node_has_fielded_children?(node)
        return true if node.is_type?(:fielded)
        return false if node.is_type?(:tokens)
        node.children.any? { |child| node_has_fielded_children?(child) }
      end
    end
  end
end
