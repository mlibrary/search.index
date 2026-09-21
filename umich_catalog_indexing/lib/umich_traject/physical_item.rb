module Traject
  module UMich
    class PhysicalItem
      # A mapping of the 974 field of bib record. When alma enriches a Bib
      # record with item information, the physical item information is put in
      # the 974 field. This class names the fields and further enriches the
      # given item information.
      #
      # @param item [MARC::DataField] A 974 field from a Marc Record
      # @param has_finding_aid [Boolean] Whether or not the holding has a
      # finding aid.
      def initialize(item:, has_finding_aid:)
        @item = item
        @has_finding_aid = has_finding_aid
      end

      # Returns an item's barcode
      #
      # @return [String] if subfield $a exists
      # @return [Nil] if subfield $a does not exist
      def barcode
        @item["a"]
      end

      # Returns a Boolean of whether or not the item should be suppressed. This
      # item suppression is in addition the suppression that Alma already does.
      #
      # The process statuses came from Aleph. CA is "Cancelled", WN and WD are
      # "withdrawn". The Library ELEC is for electronic resources that didn't
      # get transfered properly from Aleph. The Library SDR is for HathiTrust
      # records where we are the keeper of the metadata but the item(s) are not
      # actually in our collection. We ultimately show those records through
      # processing the zephir records
      #
      # @return [Boolean] whether or not the item should be suppressed
      def should_be_suppressed
        /Process Status: (CA|WN|WD)/.match?(@item["y"]) ||
          ["ELEC", "SDR"].include?(library)
      end

      def callnumber
        @item["h"]
      end

      # Returns a Boolean of whether or not the item should get a "Reserve This"
      # link in Library Search. Items with a finding aid get a "Finding Aid" link
      # instead of a "Reserve This" link
      #
      # @return [Boolean] whether or not item should have a "Reserve This" link
      # in Library Search
      def can_reserve?
        ["BENT", "CLEM", "SPEC"].include?(library) && !finding_aid?
      end

      def description
        @item["z"]
      end

      def display_name
        ::UMich::LibLocInfo.display_name(library, location)
      end

      def fulfillment_unit
        ::UMich::LibLocInfo.fulfillment_unit(library, location)
      end

      def location_type
        ::UMich::LibLocInfo.location_type(library, location)
      end

      def info_link
        ::UMich::LibLocInfo.info_link(library, location)
      end

      def inventory_number
        @item["i"]
      end

      def item_id
        @item["7"]
      end

      def item_policy
        @item["p"]
      end

      def library
        @item["b"]
      end

      def location
        @item["c"]
      end

      # A list of locations associated with the item, where locations include the
      # Library code and the "Library Code Location Code" combination. This is
      # added to the locations solr field.
      #
      # @return [Array] an array of library codes and "library location" codes
      def locations
        [library, "#{library} #{location}".strip].uniq
      end

      def permanent_library
        @item["d"]
      end

      def permanent_location
        @item["e"]
      end

      def process_type
        @item["t"]
      end

      def public_note
        @item["n"]
      end

      def finding_aid?
        @has_finding_aid
      end

      def material_type
        @item["m"]
      end

      def temp_location?
        library != permanent_library || location != permanent_location
      end

      def circulating?
        @item["f"] == "1"
      end

      # Hash summary of what is in the item. This is what is added to the
      # items array for a given holding in the "hol" solr field
      #
      # @returns [Hash] summary of the item
      def to_h
        {
          barcode: barcode,
          library: library,
          location: location,
          info_link: info_link,
          display_name: display_name,
          fulfillment_unit: fulfillment_unit,
          location_type: location_type,
          can_reserve: can_reserve?,
          permanent_library: permanent_library,
          permanent_location: permanent_location,
          temp_location: temp_location?,
          callnumber: callnumber,
          public_note: public_note,
          process_type: process_type,
          item_policy: item_policy,
          description: description,
          inventory_number: inventory_number,
          item_id: item_id,
          material_type: material_type,
          record_has_finding_aid: finding_aid?
        }
      end
    end
  end
end
