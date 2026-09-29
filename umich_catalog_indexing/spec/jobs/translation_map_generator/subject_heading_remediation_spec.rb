require_relative "../../spec_helper"
require "jobs"

def remediated_term
  {"a" => ["Undocumented immigrants"]}
end

def mexico_remediated_term
  {"a" => ["Mexico, Gulf of, Watershed"]}
end

def deprecated_terms
  [
    {
      "a" => ["Aliens"],
      "x" => ["Legal status, laws, etc."]
    },
    {
      "a" => ["Illegal aliens"],
      "x" => ["Legal status, laws, etc."]
    },
    {
      "a" => ["Undocumented foreign nationals"]
    },
    {
      "a" => ["Illegal aliens"]
    },
    {
      "a" => ["Aliens, Illegal"]
    },
    {
      "a" => ["Illegal immigrants"]
    },
    {
      "a" => ["Undocumented noncitizens"]
    }
  ]
end

def mexico_deprecated_terms
  [
    {
      "a" => ["America, Gulf of, Watershed"]
    },
    {
      "a" => ["Test Test Test"]
    }
  ]
end
describe Jobs::TranslationMapGenerator::SubjectHeadingRemediation::Set do
  before(:each) do
    @data = fixture("subjects/authority_set.json")
  end
  let(:set_id) { "1234" }
  let(:authority_record_id) { "98187481368106381" }
  let(:authority_record) { fixture("subjects/authority_record.json") }
  let(:second_authority_record_id) { "999" }
  let(:second_authority_record) { fixture("subjects/authority_record2.json") }
  let(:stub_set_request) {
    stub_alma_get_request(
      url: "conf/sets/#{set_id}/members",
      query: {limit: 100, offset: 0},
      output: @data
    )
  }
  let(:stub_authority_request) {
    stub_alma_get_request(
      url: "bibs/authorities/#{authority_record_id}",
      query: {view: "full"},
      output: authority_record
    )
  }
  let(:stub_second_authority_request) {
    stub_alma_get_request(
      url: "bibs/authorities/#{second_authority_record_id}",
      query: {view: "full"},
      output: second_authority_record
    )
  }
  subject do
    described_class.new(JSON.parse(@data))
  end
  context "#ids" do
    it "returns an array of ids" do
      expect(subject.ids).to contain_exactly(authority_record_id)
    end
  end

  context "#authority_records" do
    it "returns an array of Authority objects" do
      stub_authority_request
      expect(subject.authority_records.first.remediated_term).to eq({"a" => ["Undocumented immigrants"]})
    end
  end

  context "#to_a" do
    it "returns an array of authority objects" do
      # Add an extra member to json
      d = JSON.parse(@data)
      d["member"].push({"id" => "999", "description" => "string"})
      @data = d.to_json
      stub_authority_request
      stub_second_authority_request

      expect(subject.to_a).to eq(
        [
          {
            "1xx" => remediated_term,
            "4xx" => deprecated_terms
          },
          {
            "1xx" => {
              "a" => ["Whatever"],
              "x" => ["First x field", "Second x field"],
              "v" => ["First v field", "Second v field"],
              "y" => ["First y field", "Second y field"],
              "z" => ["First z field", "Second z field"]
            },
            "4xx" => [
              {
                "a" => ["Stuff"],
                "x" => ["First deprecated x field", "Second deprecated x field"],
                "v" => ["First deprecated v field", "Second deprecated v field"],
                "y" => ["First deprecated y field", "Second deprecated y field"],
                "z" => ["First deprecated z field", "Second deprecated z field"]
              }
            ]
          }
        ]
      )
    end
  end
  context ".for" do
    it "returns a Set from the Alma Set id" do
      stub_set_request
      expect(described_class.for(set_id).ids.first).to eq(authority_record_id)
    end
    it "errors out if it can't talk to alma" do
      stub_alma_get_request(
        url: "conf/sets/#{set_id}/members",
        query: {limit: 100, offset: 0},
        no_return: true
      ).to_timeout
      expect { described_class.for(set_id) }.to raise_error(StandardError, /#{set_id}/)
    end
  end
end
describe Jobs::TranslationMapGenerator::SubjectHeadingRemediation::Authority do
  let(:geo_authority_record) { JSON.parse(fixture("subjects/geo_authority_record.json")) }
  before(:each) do
    @data = JSON.parse(fixture("subjects/authority_record.json"))
  end
  subject do
    described_class.new(@data)
  end
  let(:authority_record_id) { "12345" }
  context ".for" do
    it "errors out if it can't talk to Alma" do
      stub_alma_get_request(
        url: "bibs/authorities/#{authority_record_id}",
        query: {view: "full"},
        status: 500
      )
      expect { described_class.for(authority_record_id) }.to raise_error(StandardError, /#{authority_record_id}/)
    end
  end
  context "#remediated_term" do
    it "returns the remediated term in the 1xx" do
      expect(subject.remediated_term).to eq(remediated_term)
    end
    it "returns the remediated term in the 151" do
      @data = geo_authority_record
      expect(subject.remediated_term).to eq(mexico_remediated_term)
    end
  end
  context "#deprecated_terms" do
    it "returns the deprecated terms from the 4xx field" do
      expect(subject.deprecated_terms).to contain_exactly(*deprecated_terms)
    end
    it "returns the deprecated terms from the 451 field" do
      @data = geo_authority_record
      expect(subject.deprecated_terms).to contain_exactly(*mexico_deprecated_terms)
    end
  end
  context "#main_to_h" do
    it "returns the expected remediated/deprecated hash" do
      expect(subject.main_to_h).to eq({
        "1xx" => remediated_term,
        "4xx" => deprecated_terms
      })
    end
  end
  context "#geo_remediated_term" do
    it "returns the value for the 781" do
      @data = geo_authority_record
      expect(subject.geo_remediated_term).to eq({"z" => ["Mexico, Gulf of, Watershed"]})
    end
    it "is nil when there is no 781" do
      expect(subject.geo_remediated_term).to be_nil
    end
  end
  context "#geo_deprecated_terms" do
    it "returns the deprecated fields but moves them to the z" do
      @data = geo_authority_record
      z_mexico_deprecated = mexico_deprecated_terms.map do |t|
        {"z" => t["a"]}
      end
      expect(subject.geo_deprecated_terms).to contain_exactly(*z_mexico_deprecated)
    end
  end

  context "#geo_to_h" do
    it "returns the geo fields remediated/deprecated" do
      @data = geo_authority_record
      expect(subject.geo_to_h).to eq({
        "1xx" => {"z" => ["Mexico, Gulf of, Watershed"]},
        "4xx" => [
          {
            "z" => ["America, Gulf of, Watershed"]
          },
          {
            "z" => ["Test Test Test"]
          }
        ]
      })
    end
  end
  context "to_a" do
    it "returns an array with main hash when there is no geo" do
      expect(subject.to_a).to eq(
        [{
          "1xx" => remediated_term,
          "4xx" => deprecated_terms
        }]
      )
    end
    it "returns an array with both the main hash and the geo hash when there is one" do
      @data = geo_authority_record
      expect(subject.to_a.size).to eq(2)
    end
  end
end
