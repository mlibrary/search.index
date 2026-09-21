require "webmock/rspec"
require "alma_rest_client"
require "debug"
require "simplecov"

ENV["APP_ENV"] = "test"
require_relative "../lib/jobs"

SimpleCov.start

RSpec.configure do |config|
  include AlmaRestClient::Test::Helpers

  config.expect_with :rspec do |expectations|
    expectations.include_chain_clauses_in_custom_matcher_descriptions = true
  end

  config.mock_with :rspec do |mocks|
    mocks.verify_partial_doubles = true
  end

  config.shared_context_metadata_behavior = :apply_to_host_groups

  config.around(:each) do |example|
    S.overlap_db.transaction(rollback: :always) do
      example.run
    end
  end
end
def fixture(path)
  File.read("./spec/fixtures/#{path}")
end

def get_record(path)
  MARC::XMLReader.new(path).first
end
