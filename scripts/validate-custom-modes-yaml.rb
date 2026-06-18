#!/usr/bin/env ruby
# frozen_string_literal: true

require "yaml"
require "pathname"

ROOT = Pathname.new(__dir__).parent.expand_path
RULES_DIR = ROOT.join("rules")
ALL_AGENTS = ROOT.join("all-agents.yaml")
REQUIRED_MODE_KEYS = %w[slug name roleDefinition groups customInstructions].freeze

def fail!(message)
  warn message
  exit 1
end

def load_yaml(path)
  YAML.safe_load_file(path.to_s, aliases: false)
rescue Psych::SyntaxError => e
  fail!("YAML parse failed: #{path.relative_path_from(ROOT)}: #{e.message}")
end

def validate_yaml_shape(path)
  rel = path.relative_path_from(ROOT)
  data = load_yaml(path)
  fail!("#{rel}: top-level YAML must be mapping") unless data.is_a?(Hash)
  fail!("#{rel}: missing customModes") unless data.key?("customModes")
  fail!("#{rel}: customModes must be list") unless data["customModes"].is_a?(Array)

  data["customModes"].each_with_index do |mode, index|
    fail!("#{rel}: customModes[#{index}] must be mapping") unless mode.is_a?(Hash)
    REQUIRED_MODE_KEYS.each do |key|
      fail!("#{rel}: customModes[#{index}] missing #{key}") unless mode.key?(key)
    end
    fail!("#{rel}: #{mode['slug']}: source must be top-level only") if mode.key?("source")
    fail!("#{rel}: #{mode['slug']}: groups must be list") unless mode["groups"].is_a?(Array)
    unless mode["customInstructions"].is_a?(String)
      fail!("#{rel}: #{mode['slug']}: customInstructions must be string")
    end
  end

  data
end

def validate_broken_patterns(path)
  rel = path.relative_path_from(ROOT)
  custom_modes_top_level_count = 0
  source_top_level_count = 0

  path.readlines(encoding: "UTF-8").each_with_index do |line, index|
    line_no = index + 1
    fail!("#{rel}:#{line_no}: customInstructions block scalar content is on same line") if line =~ /customInstructions:[ \t]*\|-[ \t]+\S/
    fail!("#{rel}:#{line_no}: customModes list is on same line") if line.include?("customModes: -")
    fail!("#{rel}:#{line_no}: source/customModes concatenated") if line.include?("source: project customModes:")
    fail!("#{rel}:#{line_no}: mode mapping keys are concatenated") if line =~ /- slug: 'architect' name:/
    custom_modes_top_level_count += 1 if line =~ /^customModes:/
    source_top_level_count += 1 if line =~ /^source:/
  end

  fail!("#{rel}: top-level customModes must appear exactly once") unless custom_modes_top_level_count == 1
  fail!("#{rel}: top-level source must not be duplicated") if source_top_level_count > 1
end

files = RULES_DIR.glob("*.yaml").sort + [ALL_AGENTS]
data_by_path = {}

files.each do |path|
  data_by_path[path] = validate_yaml_shape(path)
  validate_broken_patterns(path)
end

rule_mode_count = RULES_DIR.glob("*.yaml").sort.sum { |path| data_by_path[path]["customModes"].length }
all_agents_count = data_by_path[ALL_AGENTS]["customModes"].length

fail!("all-agents.yaml: customModes count #{all_agents_count} does not match rules count #{rule_mode_count}") unless all_agents_count == rule_mode_count

puts "yaml ok"
puts "broken pattern check ok"
puts "all-agents.yaml customModes count = #{all_agents_count}"
