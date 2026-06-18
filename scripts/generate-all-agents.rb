#!/usr/bin/env ruby
# frozen_string_literal: true

require "yaml"
require "psych"
require "pathname"

ROOT = Pathname.new(__dir__).parent.expand_path
RULES_DIR = ROOT.join("rules")
ALL_AGENTS = ROOT.join("all-agents.yaml")
REQUIRED_MODE_KEYS = %w[slug name roleDefinition groups customInstructions].freeze
BROKEN_PATTERNS = {
  "customModes: -" => "customModes list must start on the next line",
  /customInstructions:[ \t]*\|-[ \t]+\S/ => "customInstructions block scalar content must start on the next line",
  "source: project customModes:" => "source and customModes must not be concatenated",
  /- slug: 'architect' name:/ => "mode mapping keys must not be concatenated"
}.freeze

module CustomModesYamlStyles
  def visit_Hash(hash)
    node = super
    node.style = Psych::Nodes::Mapping::BLOCK
    node.children.each_slice(2) do |key_node, value_node|
      next unless key_node.is_a?(Psych::Nodes::Scalar)

      key_node.style = Psych::Nodes::Scalar::PLAIN
      next unless key_node.value == "customInstructions" && value_node.is_a?(Psych::Nodes::Scalar)

      value_node.style = Psych::Nodes::Scalar::LITERAL
      value_node.plain = false
      value_node.quoted = true
    end
    node
  end

  def visit_Array(array)
    node = super
    node.style = Psych::Nodes::Sequence::BLOCK
    node
  end
end

Psych::Visitors::YAMLTree.prepend(CustomModesYamlStyles)

def emit_document(data)
  YAML.dump(data, nil, indentation: 2, line_width: -1)
end

def load_yaml_mapping(path)
  data = YAML.safe_load_file(path.to_s, aliases: false)
  raise "#{path}: top-level YAML must be mapping" unless data.is_a?(Hash)

  data
rescue Psych::SyntaxError => e
  raise "#{path}: YAML parse failed: #{e.message}"
end

def validate_mode!(path, mode, index)
  raise "#{path}: customModes[#{index}] must be mapping" unless mode.is_a?(Hash)

  REQUIRED_MODE_KEYS.each do |key|
    raise "#{path}: customModes[#{index}] missing #{key}" unless mode.key?(key)
  end
  raise "#{path}: #{mode['slug']}: groups must be list" unless mode["groups"].is_a?(Array)
  raise "#{path}: #{mode['slug']}: customInstructions must be string" unless mode["customInstructions"].is_a?(String)
end

def load_rule_modes(path)
  data = load_yaml_mapping(path)
  modes = data["customModes"]
  raise "#{path}: missing customModes" unless modes
  raise "#{path}: customModes must be list" unless modes.is_a?(Array)
  raise "#{path}: customModes must contain exactly one mode" unless modes.length == 1

  modes.each_with_index { |mode, index| validate_mode!(path, mode, index) }
  modes.map { |mode| mode.reject { |key, _| key == "source" } }
end

def write_rule_file(path, modes)
  path.write(emit_document({ "customModes" => modes, "source" => "project" }), encoding: "UTF-8")
end

def validate_document!(path, expected_count: nil)
  text = path.read(encoding: "UTF-8")
  BROKEN_PATTERNS.each do |pattern, message|
    matched = pattern.is_a?(Regexp) ? text.match?(pattern) : text.include?(pattern)
    raise "#{path}: #{message}" if matched
  end

  data = YAML.safe_load(text, aliases: false)
  raise "#{path}: top-level YAML must be mapping" unless data.is_a?(Hash)
  raise "#{path}: customModes must be list" unless data["customModes"].is_a?(Array)
  raise "#{path}: customModes count mismatch" if expected_count && data["customModes"].length != expected_count

  data["customModes"].each_with_index { |mode, index| validate_mode!(path, mode, index) }
  data
rescue Psych::SyntaxError => e
  raise "#{path}: YAML parse failed after generation: #{e.message}"
end

write_rules = ARGV.include?("--write-rules")
rule_paths = RULES_DIR.glob("*.yaml").sort
all_modes = []

rule_paths.each do |path|
  modes = load_rule_modes(path)
  write_rule_file(path, modes) if write_rules
  validate_document!(path, expected_count: modes.length) if write_rules
  all_modes.concat(modes)
end

ALL_AGENTS.write(emit_document({ "customModes" => all_modes, "source" => "project" }), encoding: "UTF-8")
validate_document!(ALL_AGENTS, expected_count: all_modes.length)
puts "generated #{ALL_AGENTS.relative_path_from(ROOT)} with #{all_modes.length} custom modes"
puts "normalized #{rule_paths.length} rule files" if write_rules
