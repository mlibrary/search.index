module Indexer
  module IndexUpdate
    def self.queue_for(environment)
      (environment == "reindex") ? "reindex" : "default"
    end

    def self.solrs_for(environment)
      if environment == "reindex"
        [S.reindex_solr_url]
      elsif S.solrcloud_on?
        [S.live_solr_url]
      else
        S.production_solr_urls
      end
    end

    def self.zephir(date:, environment:, solrs:, async: true)
      S.logger.info "Start indexing zephir metadata updates for #{date}"

      zephir_file = Jobs::Utilities::ZephirFile.daily_update(date)
      zephir_file_basename = zephir_file.split(".").first

      paths = SFTP.client.ls("#{S.zephir_update_dir_path}/#{zephir_file_basename}_*")

      run(environment: environment, async: async, klass: IndexJson, paths: paths, solrs: solrs)

      S.logger.info "Finished indexing zephir metadata updates for #{date}"
    end

    def self.alma(date:, environment:, solrs:, async: true)
      if async
      else
        S.logger.info "Start indexing alma metadata updates for #{date}"
      end

      date_str = date.strftime("%Y%m%d") # must be a string in the form YYYYMMDD
      delete_paths = S.alma_update_file_paths.select { |x| x.match?(/^.*#{date_str}.*_delete_?\d?\d?\.tar/) }
      new_paths = S.alma_update_file_paths.select { |x| x.match?(/^.*#{date_str}.*_new_?\d?\d?\.tar/) }

      run(environment: environment, async: async, klass: IndexIt, paths: new_paths, solrs: solrs)
      run(environment: environment, async: async, klass: DeleteIt, paths: delete_paths, solrs: solrs)
      S.logger.info "Finished alma metadata updates for #{date}"
    end

    def self.run(environment:, klass:, paths:, solrs:, async: true)
      solrs = solrs_for(environment) if solrs.nil?
      solrs.each do |solr_url|
        paths.each do |path|
          S.logger.info "#{klass} for #{path} into #{environment} solr: #{solr_url}"
          if async
            klass.set(queue: queue_for(environment)).perform_async(path, solr_url)
          else
            klass.new.perform(path, solr_url)
          end
        end
      end
    end
  end
end
