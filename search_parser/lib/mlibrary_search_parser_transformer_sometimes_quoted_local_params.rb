module MLibrarySearchParser
  module Transformer
    module Solr
      class SometimesQuotedLocalParams < LocalParams
        # @override
        # @param [MLibrarySearchParser::Node::BaseNode] node
        def edismaxify(field, node)
          q_localparams_name = "q#{node.number}"
          qq_localparams_name = "qq#{node.number}"
          tokens_name = "t#{node.number}"

          set_param(q_localparams_name, node.clean_string)
          set_param(qq_localparams_name, lucene_escape(node.tokens_phrase))
          set_param(tokens_name, lucene_escape(node.wanted_tokens_string))

          attributes = field_config(field)
          args = attributes.keys.each_with_object({}) do |k, h|
            v = attributes[k]
            fname = "#{field}_#{k}"
            v = v.to_s
            v = v.to_s.gsub(/\$q\b/, "$" + q_localparams_name)
            v = v.gsub(/\$qq\b/, "$" + qq_localparams_name)
            v = v.gsub(/\$t\b/, "$" + tokens_name)
            v = v.gsub(/[\n\s]+/, " ")
            set_param(fname, v)
            h[k] = "$#{fname}"
          end

          args = default_attributes.merge(args)

          # If the node is a boolean, we need to get rid of the mm parameter
          # because edismax with bools and mm just don't play well together.
          #
          # See https://blog.innoventsolutions.com/innovent-solutions-blog/2017/02/solr-edismax-boolean-query.html
          # and/or SOLR-8812

          if [:and, :or].include? node.node_type
            args.delete("mm")
          end
          arg_pairs = args.each_pair.map { |k, v| "#{k}=#{v}" }

          if field == "title_starts_with"
            "{!edismax #{arg_pairs.join(" ")} v=$#{qq_localparams_name}}"
          else
            "{!edismax #{arg_pairs.join(" ")} v=$#{q_localparams_name}}"
          end
        end
      end
    end
  end
end
