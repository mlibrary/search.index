require "thor"
require "services"
require "sidekiq_jobs"
require "traject"
require "indexer/index_full"
require "indexer/index_update"
require "indexer/filter_zephir"
require "debug/prelude"

def get_file_names(dir)
  Dir.children("#{S.project_root}/#{dir}").map { |x| File.basename(x, ".rb") }
end

module Indexer
  class CLI < Thor
    def self.exit_on_failure?
      true
    end

    desc "index_a_file METADATA_FILE_PATH", "produces flat file output from traject"
    option :reader, aliases: ["r"], desc: "what kind of reader should be used", enum: get_file_names("readers"), default: "xml"
    option :writer, aliases: ["w"], desc: "what kind of writer should be used", enum: get_file_names("writers"), default: "debug"
    def index_a_file(metadata_file_path)
      config = [
        "indexers/settings.rb",
        "indexers/common.rb",
        "indexers/common_ht.rb",
        "indexers/subject_topic.rb",
        "indexers/umich.rb",
        "indexers/umich_alma.rb",
        "indexers/callnumbers.rb"
      ]
      config.prepend("/readers/#{options[:reader]}.rb")
      config.prepend("/writers/#{options[:writer]}.rb")
      indexer = Traject::Indexer::MarcIndexer.new(logger: S.logger) do |ind|
        config.each { |config_path| load_config_file(File.join(S.project_root, config_path)) }
      end
      success = indexer.process File.open(metadata_file_path, "r")
      unless success
        fatal "traject failed, shutting down"
      end
    end

    desc "index_full", "looks up the latest full metadata files and queues them up for the reindex solr"
    option :source, aliases: ["s"], desc: "Where is the metadata from?", enum: ["alma", "zephir"], required: true, repeatable: true
    def index_full
      options[:source].each do |source|
        Indexer::IndexFull.public_send(source)
      end
    end

    desc "filter_zephir full||today||yyyy-mm-dd", "Filter zephir metadata for umich public domain that's not in alma."
    def filter_zephir(date)
      unless ["full", "today"].include?(date)
        date = Date.parse(date)
      end

      fz = Indexer::FilterZephir
      config = case date
      when "full"
        fz.full_config
      when "today"
        fz.today_config
      else
        fz.date_config(date)
      end
      fz.run(**config)
    end

    desc "index_update", "Looks up the update metadata files and queues them up for the production solrs"
    option :source, aliases: ["s"], desc: "Where is the metadata from?", enum: ["alma", "zephir"], required: true, repeatable: true
    option :date, aliases: ["d"], desc: "Date of file to index. If 'today' is passed, it will look up the most recent update for the source(s). For zephir files, it will look up yesterday's file.", default: "today"
    option :environment, aliases: ["e"], desc: "Which solr(s) to send the update to. If async, production goes to the default queue, reindex goes to the reindex queue", default: "production", enum: ["production", "reindex"]
    option :solr_url, desc: "Specific solr url to send to. This overrides the solrs that would be used based on the environment option", repeatable: true
    option :async, aliases: ["a"], desc: "Send the job to run asynchronously or run it now", type: :boolean, default: true
    def index_update
      date = if options["date"] == "today"
        Date.today
      else
        Date.parse(options["date"])
      end

      options[:source].each do |source|
        Indexer::IndexUpdate.public_send(source, date: date, environment: options[:environment], async: options[:async], solrs: options[:solr_url])
      end
    end

    desc "catch_up", "indexes the updates from a given date to today."
    option :source, aliases: ["s"], desc: "Where is the metadata from?", enum: ["alma", "zephir"], required: true, repeatable: true
    option :date, aliases: ["d"], desc: "Date from which to catchup from. Default is the first of the current month"
    option :environment, aliases: ["e"], desc: "Which solr(s) to send the update to.", default: "reindex", enum: ["production", "reindex"]
    option :solr_url, desc: "Specific solr url to send to. This overrides the solrs that would be used based on the environment option", repeatable: true
    def catch_up
      start_date = if options["date"].nil?
        Date.new(Date.today.year, Date.today.month, 1) # First of the month
      else
        Date.parse(options["date"])
      end

      start_date.upto(DateTime.now) do |date|
        date_string = date.strftime("%Y-%m-%d")
        S.logger.info ""
        S.logger.info "========================"
        S.logger.info "Start #{date_string}"
        S.logger.info "========================"
        S.logger.info ""
        options[:source].each do |source|
          Indexer::IndexUpdate.public_send(source, date: date, environment: options[:environment], async: false, solrs: options[:solr_url])
        end
        S.logger.info ""
        S.logger.info "========================"
        S.logger.info "Finish #{date_string}"
        S.logger.info "========================"
        S.logger.info ""
      end
      S.logger.info "========================"
      S.logger.info "Finish Catch up from #{start_date.strftime("%Y-%m-%d")}"
      S.logger.info "========================"
    end

    desc "generate_translation_map", "Generates the given translation map"
    option :force, aliases: ["f"], desc: "Force generation of given translation map even if it is less than one day old", default: false, type: :boolean
    option :tm, repeatable: true, enum: ["floor_location", "electronic_collections", "electronic_collections_ranking"], required: true
    def generate_translation_map
      tm_map = {
        "floor_location" => Jobs::TranslationMapGenerator::FloorLocations,
        "electronic_collections" => Jobs::TranslationMapGenerator::ElectronicCollections,
        "electronic_collections_ranking" => Jobs::TranslationMapGenerator::ElectronicCollectionsRanking
      }

      options[:tm].each do |tm|
        Jobs::TranslationMapGenerator.generate(generator: tm_map[tm], force: options["force"])
      end
    end
  end
end
