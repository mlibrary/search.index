describe SearchParser::Datastore::Primo do
  context ".primo_q" do
    def expect_primo_q(input, output)
      primo = SearchParser.get_datastore(:articles)
      expect(primo.primo_q(input)).to eq(output)
    end
    it "returns expected q string for basic query" do
      expect_primo_q("birds", "any,contains,birds")
    end
    it "handles keyword AND title field" do
      expect_primo_q("birds AND title:(greece)", "any,contains,birds,AND;title,contains,greece")
    end
    it "handles exact keyword" do
      expect_primo_q("exact:(birds)", "any,exact,birds")
    end
    it "handles or with issn" do
      expect_primo_q("exact:(birds) OR issn:(1759-5045)", "any,exact,birds,OR;issn,contains,1759-5045")
    end
    it "handles nor with topic" do
      expect_primo_q("subject:(openalex) NOT title:(birds)", "topic,contains,openalex,NOT;title,contains,birds")
    end
    it "groups OR fields" do
      expect_primo_q("stuff OR things OR music", "any,contains,(stuff OR (things OR music))")
    end
    it "handles complex boolean" do
      expect_primo_q("subject:(openalex) NOT title:(birds) NOT (bugs) AND (health) OR (stuff)", "topic,contains,openalex,NOT;title,contains,birds,AND;any,contains,(((bugs) AND health) OR stuff)")
    end
    it "handles apples NOT oranges" do
      expect_primo_q("apple NOT orange", "any,contains,apple,NOT;any,contains,orange")
    end
    it "handles mitt romney" do
      expect_primo_q('"mitt romney" OR "Romney, Mitt" NOT "Standalone Media Collections"', "any,contains,(\"mitt romney\" OR \"Romney, Mitt\"),NOT;any,contains,\"Standalone Media Collections\"")
    end
    it "handles twain finn" do
      expect_primo_q("title:finn OR author:twain", "title,contains,finn,OR;creator,contains,twain")
    end
  end
end
