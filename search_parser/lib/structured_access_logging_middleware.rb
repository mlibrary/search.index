require "semantic_logger"
require "rack"

# This is largely taken from Rack::CommonLogger. It assumes you are using
# SemanticLogger for logs.
class StructuredAccessLoggingMiddleware
  attr_reader :app
  include Rack

  def initialize(app)
    @app = app
    @logger = SemanticLogger["access_log"]
  end

  # Common Log Format (2.5): https://httpd.apache.org/docs/trunk/logs.html#accesslog
  #
  # The actual format is slightly different than the above due to the
  # inclusion of referer, user_agent, and elapsed time in seconds

  # Log all requests in common_log format after a response has been
  # returned.  Note that if the app raises an exception, the request
  # will not be logged, so if exception handling middleware are used,
  # they should be loaded after this middleware.  Additionally, because
  # the logging happens after the request body has been fully sent, any
  # exceptions raised during the sending of the response body will
  # cause the request not to be logged.
  def call(env)
    began_at = Rack::Utils.clock_time
    status, headers, body = response = @app.call(env)

    response[2] = Rack::BodyProxy.new(body) { log(env, status, headers, began_at) }
    response
  end

  private

  # Log the request to the configured logger.
  def log(env, status, response_headers, began_at)
    request = Rack::Request.new(env)
    span = request.get_header("otel.rack.token_and_span")[1]

    record = {
      host: request.ip,
      user: request.get_header("REMOTE_USER"),
      method: request.request_method,
      path: request.path_info,
      protocol: request.get_header("HTTP_VERSION"),
      query_string: (request.query_string.empty? ? nil : "?#{request.query_string}"),
      status: status,
      size: response_headers[CONTENT_LENGTH].to_i,
      referer: request.referer,
      user_agent: request.user_agent,
      elapsed_time_in_seconds: (Rack::Utils.clock_time - began_at)
    }

    SemanticLogger.tagged(
      trace_id: span.context.valid? ? span.context.hex_trace_id : nil,
      span_id: span.context.valid? ? span.context.hex_span_id : nil
    ) do
      @logger << record
    end
  end
end
