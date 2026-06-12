# Jekyll::Post 在 Jekyll 3+ 已移除，仅保留 Jekyll::Page
class Jekyll::Page

  def relative
    depth = [url.split("/").length - 2, 0].max
    "../" * depth
  end

  def to_liquid(attrs = ATTRIBUTES_FOR_LIQUID)
    super(attrs + %w[
          relative
    ])

  end
end
