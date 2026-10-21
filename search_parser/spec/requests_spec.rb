RSpec.describe "requests" do
  def gen_solr_stub(key, value, solr_url = S.solr_url, core = S.solr_core)
    # this should do proper matching.
    # (?=&|\z) means the string is followed by either the "&" character or
    # the end of the string
    stub_request(:get, /#{solr_url}\/solr\/#{core}\/select.*[?&]#{key}=#{value}(?=&|\z)/)
  end
  let(:key) { "" }
  let(:value) { "" }
  let(:params) do
    {query: "blah"}
  end
  context "get /catalog/search" do
    def expect_has_param(key, value)
      solr_stub = gen_solr_stub(key, value)
      get "/catalog/search", params
      expect(solr_stub).to have_been_requested
    end

    context "standard params" do
      it "has a q1 param" do
        expect_has_param("q1", "blah")
      end
      it "has fl of *,score" do
        expect_has_param("fl", '\*,score')
      end
      it "has a default start of 0" do
        expect_has_param("start", "0")
      end
      it "uses start from query parameters" do
        params[:start] = "22"
        expect_has_param("start", "22")
      end
      it "has a default rows of 10" do
        expect_has_param("rows", "10")
      end
      it "uses the rows param for rows" do
        params[:rows] = "20"
        expect_has_param("rows", "20")
      end
      it "has a default for sort" do
        expect_has_param("sort", "score desc")
      end
      it "uses the sort param for sort" do
        params["sort"] = "created asc"
        expect_has_param("sort", "created asc")
      end
      it "includes solr quoted string for qq" do
        expect_has_param("qq", '"_query_.*')
      end
    end

    SearchParser.get_datastore(:catalog).facets.each do |facet|
      context "#{facet} parameters" do
        it "has the default facet limit" do
          expect_has_param("f.#{facet}.facet.limit", "50")
        end
        it "has the default facet mincount" do
          expect_has_param("f.#{facet}.facet.mincount", "1")
        end
        it "has the default facet offset" do
          expect_has_param("f.#{facet}.facet.offset", "0")
        end
        it "has the default facet sort" do
          expect_has_param("f.#{facet}.facet.sort", "count")
        end
        it "has the facet field" do
          expect_has_param("f.#{facet}.facet.sort", "count")
        end
      end
    end

    context "filter query" do
      it "passes the filter query from fq param" do
        params["fq"] = ["first", "second"]
        expect_has_param("fq", "first")
      end
      it "includes the second parameter too" do
        params["fq"] = ["first", "second"]
        expect_has_param("fq", "second")
      end

      # these two won't last for ever. The api should always send a fq
      it "defaults to um library" do
        expect_has_param("fq", "institution.*")
      end
      it "defaults to not-search-only" do
        expect_has_param("fq", '%2B\(availability:physical.*')
      end
    end
  end
  context "get /catalog/academic_disciplines" do
    def expect_has_param(key, value)
      solr_stub = gen_solr_stub(key, value)
      get "/catalog/academic_disciplines", params
      expect(solr_stub).to have_been_requested
    end

    context "standard params" do
      it "has a q1 param" do
        expect_has_param("q1", "blah")
      end
      it "has fl of hlb3Str" do
        expect_has_param("fl", "hlb3Str")
      end
      it "has a start of 0" do
        expect_has_param("start", "0")
      end
      it "has a rows of " do
        expect_has_param("rows", "100")
      end
      it "has a default for sort" do
        expect_has_param("sort", "score desc")
      end
    end
    context "filter query" do
      it "passes the filter query from fq param" do
        params["fq"] = ["first", "second"]
        expect_has_param("fq", "first")
      end
      it "includes the second parameter too" do
        params["fq"] = ["first", "second"]
        expect_has_param("fq", "second")
      end

      # these two won't last for ever. The api should always send a fq
      it "defaults to um library" do
        expect_has_param("fq", "institution.*")
      end
      it "defaults to not-search-only" do
        expect_has_param("fq", '%2B\(availability:physical.*')
      end
    end
  end
  context "get /onlinejournals/search" do
    def expect_has_param(key, value)
      solr_stub = gen_solr_stub(key, value)
      get "/onlinejournals/search", params
      expect(solr_stub).to have_been_requested
    end
    it "has location:ELEC in filter query" do
      expect_has_param("fq", "location:ELEC")
    end
    it "has format:Serial in filter query" do
      expect_has_param("fq", "format:Serial")
    end
    it "has wt json" do
      expect_has_param("wt", "json")
    end
  end
  context "get /onlinejournals/academic_disciplines" do
    def expect_has_param(key, value)
      solr_stub = gen_solr_stub(key, value)
      get "/onlinejournals/academic_disciplines", params
      expect(solr_stub).to have_been_requested
    end
    it "has location:ELEC in filter query" do
      expect_has_param("fq", "location:ELEC")
    end
    it "has format:Serial in filter query" do
      expect_has_param("fq", "format:Serial")
    end
  end
  context "get /databases/search" do
    def expect_has_param(key, value)
      solr_stub = gen_solr_stub(key, value, S.website_solr_url, S.website_solr_core)
      get "/databases/search", params
      expect(solr_stub).to have_been_requested
    end
    it "has type:database in filter query" do
      expect_has_param("fq", "type:database")
    end
  end
end
