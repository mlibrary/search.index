require "canister"
require "semantic_logger"
require "faraday"
require "httpx/adapters/faraday"

Services = Canister.new
Faraday.default_adapter = :httpx

S = Services

S.register(:app_env) { ENV["APP_ENV"] || "development" }
S.register(:app_name) { ENV["APP_NAME"] || "search_parser" }

#######
# Solr
######
S.register(:solr_url) { ENV["CATALOG_SOLR_URL"] || "http://solr:8983" }
S.register(:solr_core) { ENV["CATALOG_SOLR_CORE"] || "biblio" }
S.register(:solr_conn) do
  Faraday.new(
    url: S.solr_url, request: {params_encoder: Faraday::FlatParamsEncoder}
  ) do |f|
    f.request :json
    f.response :json
  end
end

S.register(:catalog_solr_url) { ENV["CATALOG_SOLR_URL"] || "http://solr:8983" }
S.register(:catalog_solr_core) { ENV["CATALOG_SOLR_CORE"] || "biblio" }
S.register(:catalog_solr_conn) do
  Faraday.new(
    url: S.catalog_solr_url, request: {params_encoder: Faraday::FlatParamsEncoder}
  ) do |f|
    f.request :json
    f.response :json
  end
end

S.register(:website_solr_url) { ENV["WEBSITE_SOLR_URL"] || "http://website-solr:8983" }
S.register(:website_solr_core) { ENV["WEBSITE_SOLR_CORE"] || "www.lib" }
S.register(:website_solr_conn) do
  Faraday.new(
    url: S.website_solr_url, request: {params_encoder: Faraday::FlatParamsEncoder}
  ) do |f|
    f.request :json
    f.response :json
  end
end

#######
# Logging
######

S.register(:log_stream) do
  $stdout.sync = true
  $stdout
end

S.register(:logger) do
  SemanticLogger[S.app_name]
end

S.register(:log_level) do
  ENV["DEBUG"] ? :debug : :info
end

S.register(:primo_api_key) do
  ENV["PRIMO_API_KEY"] || "primo_api_key"
end

SemanticLogger.default_level = S.log_level

if S.app_env != "test"
  SemanticLogger.on_log do |log|
    span = OpenTelemetry::Trace.current_span

    log.set_context(:trace_id, span.context.valid? ? span.context.hex_trace_id : nil)
    log.set_context(:span_id, span.context.valid? ? span.context.hex_span_id : nil)
  end
end

class ProductionFormatter < SemanticLogger::Formatters::Json
  # Leave out the pid
  def pid
  end

  def named_tags
    [:trace_id, :span_id].each do |tag|
      log.named_tags[tag] = log.context[tag] if log.named_tags[tag].nil?
    end
    super
  end

  # Leave out environment
  def environment
  end

  # Leave out application (This would be Semantic Logger, which isn't helpful)
  def application
  end
end

if S.app_env != "test"
  if $stdin.tty?
    SemanticLogger.add_appender(io: S.log_stream, formatter: :color)
  else
    SemanticLogger.add_appender(io: S.log_stream, formatter: ProductionFormatter.new)
  end
end
