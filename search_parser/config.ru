require "./app"
require "./lib/structured_access_logging_middleware"

require "opentelemetry/sdk"
require "opentelemetry/instrumentation/all"
require "opentelemetry-exporter-otlp"
OpenTelemetry::SDK.configure do |c|
  c.service_name = "parser"
  c.use_all # enables all instrumentation!
end

use Metrics::Middleware
use Rack::Deflater
use StructuredAccessLoggingMiddleware

run SearchParser::Application
