require "umich_traject"
require "ht_traject"
# require 'ht_traject/ht_overlap.rb'
require "json"
require "umich_traject/floor_location"

HathiFiles = if ENV["NODB"]
  require "ht_traject/no_db_mocks/ht_hathifiles"
  HathiTrust::NoDB::HathiFiles
else
  require "ht_traject/ht_hathifiles"
  HathiTrust::HathiFiles
end
S.logger.info(HathiFiles)

libLocInfo = Traject::TranslationMap.new("umich/libLocInfo")
electronic_collections = Traject::TranslationMap.new("umich/electronic_collections")

UMich::FloorLocation.configure("lib/translation_maps/umich/floor_locations.json")

# skip course reserve records

each_record do |r, context|
  r.each_by_tag("999") do |f|
    if f["a"] and f["a"] =~ /CR_RESTRICTED/
      id = context.output_hash["id"]
      context.skip!("#{id} : Course reserve record skipped")
    end
  end
end
# 035    $a (MiU)003113534MIU01
aleph_pattern = /^\(MiU\)\d{9}MIU01$/
to_field "aleph_id" do |record, acc, context|
  if context.clipboard[:ht][:record_source] == "alma"
    aleph_spec = Traject::MarcExtractor.cached("035a")
    aleph_spec.extract(record).grep(aleph_pattern).each { |alephnum|
      acc << alephnum[5, 9]
      break		# single-valued field, some alma records have multiple occurrences, so only use first
    }
  end
end

cc_to_of = Traject::TranslationMap.new("ht/collection_code_to_original_from")
each_record do |r, context|
  locations = []
  inst_codes = []
  context.output_hash["id"]

  # "OWN" field
  r.each_by_tag(["958", "OWN"]) do |f|
    locations << f["a"].upcase if f["a"]
    inst_codes << f["a"].upcase if f["a"]
  end

  hol_list = []
  # this is ugly--needs to be refactored
  if context.clipboard[:ht][:record_source] == "zephir"
    # cc_to_of = Traject::TranslationMap.new('ht/collection_code_to_original_from')
    # add hol for HT volumes
    items = []
    # etas_status = context.clipboard[:ht][:overlap][:count_etas] > 0 # make it a boolean
    r.each_by_tag("974") do |f|
      next unless f["u"]
      item = {}
      item[:id] = f["u"]
      item[:rights] = f["r"]
      item[:description] = f["z"]
      item[:collection_code] = f["c"]
      item[:source] = CGI.unescapeHTML(cc_to_of[f["c"].downcase])
      item[:access] = !!(item[:rights] =~ /^(pd|world|ic-world|cc|und-world)/)
      # item[:status] = statusFromRights(item[:rights], etas_status)
      item[:status] = statusFromRights(item[:rights])
      items << item
    end
    if items.any?
      hol = {}
      hol[:library] = "HathiTrust Digital Library"
      hol[:items] = sortItems(items)
      hol_list << hol
      locations << "MiU"
      inst_codes << "MIU"
      inst_codes << "MIFLIC"
    end
  else

    holdings = Traject::UMich::Holdings.new(r, context, libLocInfo, UMich::FloorLocation, HathiFiles).run

    locations.push(*holdings[:locations])
    inst_codes.push(*holdings[:inst_codes])
    hol_list.push(*holdings[:hol_list])
  end

  # TODO This is how to empty it
  if hol_list.empty?
    id = context.output_hash["id"]&.first || ""
    electronic_collections_for_id = electronic_collections[id]

    if electronic_collections_for_id

      hol_list = electronic_collections_for_id.map do |x|
        inst_codes.push(*x["institution_codes"])
        {
          link: x["link"],
          library: "ELEC",
          link_text: "Available online",
          status: x["status"],
          note: x["note"],
          collection_name: x["collection_name"],
          interface_name: x["interface_name"],
          finding_aid: false,
          campuses: x["campuses"]
        }
      end
      locations << "ELEC"
    end
    # this message is in debug
    # I think this will be check for level url (from the translation map from
    # alma api.) If so, add in that electronic item.
    # maybe look for the coming soon? I need to go look elsewhere probably
    # else suppress
  end
  context.clipboard[:ht][:hol_list] = hol_list
  context.clipboard[:ht][:locations] = locations.compact.uniq.sort
  context.clipboard[:ht][:inst_codes] = inst_codes.compact.uniq.sort
end

to_field "hol" do |record, acc, context|
  acc << context.clipboard[:ht][:hol_list].to_json
end

to_field "availability" do |record, acc, context|
  acc.replace Traject::UMich::Availability.new(context.clipboard[:ht][:hol_list]).to_a
end

to_field "new_availability" do |record, acc, context|
  acc.replace Traject::UMich::Availability.new(context.clipboard[:ht][:hol_list]).to_a
end

location_map = Traject::UMich.location_map
to_field "location" do |record, acc, context|
  locations = Array(context.clipboard[:ht][:locations])
  # acc.replace locations.map { |code| location_map[code] }
  acc.replace locations
  acc.map! { |code| location_map[code.strip] }
  acc.flatten!
  acc.uniq!
end

to_field "collection" do |record, acc, context|
  locations = Array(context.clipboard[:ht][:locations]).map { |code| location_map[code.strip] }.flatten
  acc.replace locations
  acc.map! { |library_location| Traject::UMich.collection_map(library_location) }
  acc.compact!
  acc.uniq!
end

# MIU, MIU-C, MIU-H, MIFLIC
inst_map = Traject::TranslationMap.new("umich/institution_map")
to_field "institution" do |record, acc, context|
  inst_codes = Array(context.clipboard[:ht][:inst_codes])
  # acc << 'MiU' if context.clipboard[:ht][:record_source] == 'zephir'   # add MiU as an institution for zephir records
  acc.replace inst_codes
  acc.map! { |code| inst_map[code.strip] }
  acc.flatten!
  acc.uniq!
end

#######################################
# A-Z eJournal list
# ####################################
# filters:
#  - "location:ELEC"
#  - "format:Serial"
# Map first letter of the filing title to one of
# * A,B,...,Z
# "0-9" for digits
# "Other" for anything else
#

def ejournal?(context)
  elec = context.clipboard[:ht][:hol_list].any? { |hol| [hol[:library], hol["library"]].include? "ELEC" }
  form = context.output_hash["format"]
  elec and form&.include?("Serial")
end

FILING_TITLE_880_extractor = Traject::MarcExtractor.new("245abdefgknp", alternate_script: :only)

def filing_titles_880(r)
  rv = []
  FILING_TITLE_880_extractor.each_matching_line(r) do |field, spec, extractor|
    str = FILING_TITLE_880_extractor.collect_subfields(field, spec).first
    rv << Traject::Macros::Marc21Semantics.filing_version(field, str, spec)
  end
  rv
end

STARTS_WITH_LATIN = /\A[\p{P}\p{Z}\p{Sm}\p{Sc}]*[\d\p{Latin}]/

def string_starts_with_latin(str)
  STARTS_WITH_LATIN.match? str
end

DOUBLE_BRACKET_TITLE = /\A.*[^\p{Latin}].*?\[\[\s*(\p{Latin}.*?)\]\]/

def latinized_in_double_brackets(str)
  return str if string_starts_with_latin(str)
  m = DOUBLE_BRACKET_TITLE.match(str)
  if m
    m[1]
  end
end

AFTER_EQUAL_TITLE = /\A.*[^\p{Latin}].*?\s+=\s*(\p{Latin}.*)/

def latinized_after_equal_title(str)
  return str if string_starts_with_latin(str)
  m = AFTER_EQUAL_TITLE.match(str)
  if m
    m[1]
  end
end

# Get the filing versions of the primary title and send it to solr to
# figure out where to put it in the A-Z list -- but only if it's an ejournal
#
to_field "title_initial", extract_marc_filing_version("245abdefgknp", include_original: false),
  first_only,
  trim_punctuation do |rec, acc, context|
  if !ejournal?(context)
    acc.replace []
  else
    filing_title = acc.first
    if filing_title && !string_starts_with_latin(filing_title)
      extra_filing_title = filing_titles_880(rec).select { |t| string_starts_with_latin(t) }.first
      best_guess = latinized_in_double_brackets(filing_title) || latinized_after_equal_title(filing_title) || extra_filing_title
      #      if !string_starts_with_latin(best_guess)
      #        best_guess = latinized_in_double_brackets(extra_filing_title) || latinized_after_equal_title(extra_filing_title) || filing_title
      #      end
      if best_guess and !best_guess.empty?
        acc.replace [best_guess]
        #        logger.info "A-Z List: replaced #{context.output_hash['title_common'].first} with #{best_guess}"
      end
    end
  end
end

# sorting routine for enum/chron (description) item sort
def enumcronSort a, b
  a[:sortstring] <=> b[:sortstring]
end

# Create a sortable string based on the digit strings present in an
# enumcron string

def enumcronSortString str
  rv = "0"
  str.scan(/\d+/).each do |nums|
    rv += nums.size.to_s + nums
  end
  rv
end

def sortItems arr
  # Only one? Never mind
  return arr if arr.size == 1

  # First, add the _sortstring entries
  arr.each do |h|
    # if h.has_key? 'description'
    h[:sortstring] = if h[:description]
      enumcronSortString(h[:description])
    else
      "0"
    end
  end

  # Then sort it
  arr.sort! { |a, b| enumcronSort(a, b) }

  # Then remove the sortstrings
  arr.each do |h|
    h.delete(:sortstring)
  end
  arr
end
