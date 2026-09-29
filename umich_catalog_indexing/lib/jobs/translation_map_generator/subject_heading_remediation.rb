module Jobs
  module TranslationMapGenerator
    module SubjectHeadingRemediation
      class << self
        include FileWriter

        def name
          "Subject Headings mapping"
        end

        # @returns [String] where in the translation map directory the file
        # should go
        def file_path
          File.join("umich", "subject_heading_remediation.json")
        end

        # @return [String] JSON string of mapping
        def generate
          JSON.pretty_generate(Set.for(S.subject_heading_remediation_set_id).to_a)
        end
      end

      class Set
        def self.for(id)
          resp = AlmaRestClient.client.get_all(url: "conf/sets/#{id}/members", record_key: "members")
          raise StandardError, "Couldn't retrieve authority set data for #{id}" if resp.status != 200
          new(resp.body)
        end

        def initialize(data)
          @data = data
        end

        # @return [Array<String>] an array of Authority Record ids
        def ids
          @data["member"].map { |x| x["id"] }
        end

        # @return [Array<Job::TranslationMapGenerator::SubjecHeadingRemediation::Set::Authority>]
        # an Array of Authority records
        def authority_records
          ids.map do |id|
            Authority.for(id)
          end
        end

        # @return [Array<Hash>] an Array of hashes of the hash version of
        # Job::TranslationMapGenerator::SubjecHeadingRemediation::Set::Authority objects
        def to_a
          authority_records.map { |x| x.to_a }.flatten
        end
      end

      class Authority
        AUTHORIZED_TERM_FIELDS = ["100", "110", "111", "130", "150", "151", "155"]
        VARIANT_TERM_FIELDS = ["400", "410", "411", "430", "450", "451", "455"]
        SUBFIELDS = ["a", "v", "x", "y", "z"]
        # @param authority_record_id [String] authority record id
        # @return [Job::TranslationMapGenerator::SubjecHeadingRemediation::Set::Authority] an Authority object
        def self.for(authority_record_id)
          resp = AlmaRestClient.client.get("bibs/authorities/#{authority_record_id}", query: {view: "full"})
          raise StandardError, "Couldn't retrieve authority data for #{authority_record_id}" if resp.status != 200
          new(resp.body)
        end

        # @param data [Hash] Hash of JSON response from Alma bib/authority API
        def initialize(data)
          @record = MARC::XMLReader.new(StringIO.new(data["anies"]&.first)).first
        end

        # @return [Hash] A hash of the fields for the remediated term. The
        # keys are the subfield code, the value is an array of terms for the
        # code.
        def remediated_term
          out_hash = Hash.new { |h, key| h[key] = [] }
          AUTHORIZED_TERM_FIELDS.filter_map { |f| @record.fields(f)&.first }.first.subfields.each do |sf|
            out_hash[sf.code].push(sf.value) if SUBFIELDS.include?(sf.code)
          end
          out_hash
        end

        # @return [Array<Hash>] An array of Hashes of the fields for the
        # deprecated terms. The keys of the hash are the subfield code, the
        # value is an array of terms for the code.
        def deprecated_terms
          VARIANT_TERM_FIELDS.filter_map { |f| @record.fields(f) unless @record.fields.empty? }.flatten.map do |field|
            out_hash = Hash.new { |h, key| h[key] = [] }
            field.subfields.each do |sf|
              out_hash[sf.code].push(sf.value) if SUBFIELDS.include?(sf.code)
            end
            out_hash
          end.sort do |a, b|
            b.keys.count <=> a.keys.count
          end
        end

        def geo_remediated_term
          term = @record.fields("781").find { |x| x.indicator2 == "0" }
          if term
            out_hash = Hash.new { |h, key| h[key] = [] }
            term.subfields.each do |sf|
              out_hash[sf.code].push(sf.value)
            end
            out_hash
          end
        end

        def geo_deprecated_terms
          deprecated_terms.map do |term|
            {"z" => term["a"]}
          end
        end

        # @return [Hash] a Hash version of the remediated and deprecated terms
        # for the Authority Record
        def to_h
          {
            "1xx" => remediated_term,
            "4xx" => deprecated_terms
          }
        end

        def main_to_h
          {
            "1xx" => remediated_term,
            "4xx" => deprecated_terms
          }
        end

        def geo_to_h
          {
            "1xx" => geo_remediated_term,
            "4xx" => geo_deprecated_terms
          }
        end

        def to_a
          result = [main_to_h]
          result.push geo_to_h if geo_remediated_term
          result
        end
      end
    end
  end
end
