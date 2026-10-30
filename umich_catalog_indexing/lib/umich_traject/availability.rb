module Traject
  module UMich
    class Availability
      ELECTRONIC_LIBRARIES = ["HathiTrust Digital Library", "ELEC", "ALMA_DIGITAL", "SDR"]
      ALMA_ELECTRONIC_LIBRARIES = ["ELEC", "ALMA_DIGITAL"]

      # @param hol [Array<Hash>] holding structure
      def initialize(hol)
        @hol = JSON.parse(hol.to_json)
      end

      # Record has at least one physical item
      # @return [Boolean]
      def physical?
        @hol.reject { |x| ELECTRONIC_LIBRARIES.any?(x["library"]) }.any?
      end

      # Record has at least one Hathi Trust item
      # @return [Boolean]
      def hathi_trust?
        @hol.any? { |x| x["library"] == "HathiTrust Digital Library" }
      end

      # Record has at least one Hathi Trust Full Text item
      # @return [Boolean]
      def hathi_trust_full_text?
        @hol.select do |holding|
          holding["library"] == "HathiTrust Digital Library"
        end.any? do |ht_holding|
          ht_holding["items"].any? do |item|
            _full_text_from_rights?(item["rights"])
          end
        end
      end

      # Record has at least one record from an electronic library
      # @return [Boolean]
      def electronic_holding?
        @hol.select { |x| ALMA_ELECTRONIC_LIBRARIES.any?(x["library"]) }.any?
      end

      def hathi_trust_or_electronic_holding?
        hathi_trust? || electronic_holding?
      end

      def hathi_trust_full_text_or_electronic_holding?
        hathi_trust_full_text? || electronic_holding?
      end

      # Returns an array of availabilies for the holding structure. This is the
      # method that's called by the application.
      # @return [Array<String>]
      def to_a
        [
          "physical",
          "hathi_trust",
          "hathi_trust_full_text",
          "hathi_trust_or_electronic_holding",
          "hathi_trust_full_text_or_electronic_holding"
        ].select { |x| send(:"#{x}?") }
      end

      # Does the rights code indicate that that item is availble for full text
      # viewing?
      # https://github.com/hathitrust/hathifiles/blob/main/lib/item_record.rb#L24
      # @return [Boolean]
      def _full_text_from_rights?(rights)
        /^(pdus$|pd$|world|cc|und-world|ic-world)/.match?(rights)
      end
    end
  end
end
