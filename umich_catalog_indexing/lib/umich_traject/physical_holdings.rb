class Traject::UMich::PhysicalHoldings
  include Enumerable

  def initialize(record:, holding_ids:)
    @record = record
    @holding_ids = holding_ids
  end

  def all
    @all ||= begin
      result = @holding_ids.map do |id|
        Traject::UMich::PhysicalHolding.for(record: @record, holding_id: id)
      end
      result.reject { |x| x.items.empty? }
      result
    end
  end

  def not_offsite
    all.reject { |x| x.offsite? } || []
  end

  def offsite
    @offsite ||= all.select { |x| x.offsite? }
  end

  def combined
    if offsite.any?
      not_offsite.push(Traject::UMich::PhysicalHolding::CombinedOffsite.new(offsite))
    else
      all
    end
  end

  def each(&block)
    combined.each do |item|
      block.call(item)
    end
  end
end
