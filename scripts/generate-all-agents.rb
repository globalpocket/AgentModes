#!/usr/bin/env ruby
# frozen_string_literal: true

require "yaml"
require "pathname"

ROOT = Pathname.new(__dir__).parent.expand_path
RULES_DIR = ROOT.join("rules")
ALL_AGENTS = ROOT.join("all-agents.yaml")
REQUIRED_MODE_KEYS = %w[slug name roleDefinition groups customInstructions].freeze

def quote_scalar(value)
  return "null" if value.nil?
  return value.to_s if value == true || value == false
  return value.to_s if value.is_a?(Numeric)

  s = value.to_s
  return "''" if s.empty?

  escaped = s.gsub("'", "''")
  "'#{escaped}'"
end

def emit_block_scalar(lines, indent)
  lines = [""] if lines.empty?
  lines.map { |line| "#{' ' * indent}#{line}" }.join("\n")
end

def emit_key_value(key, value, indent)
  prefix = "#{' ' * indent}#{key}:"
  case value
  when Hash
    [prefix, emit_mapping(value, indent + 2)].join("\n")
  when Array
    return "#{prefix} []" if value.empty?

    [prefix, emit_sequence(value, indent + 2)].join("\n")
  when String
    if value.include?("\n")
      lines = value.split("\n", -1)
      lines.pop if lines.last == ""
      ["#{prefix} |-", emit_block_scalar(lines, indent + 2)].join("\n")
    else
      "#{prefix} #{quote_scalar(value)}"
    end
  else
    "#{prefix} #{quote_scalar(value)}"
  end
end

def emit_mapping(hash, indent = 0)
  hash.map { |key, value| emit_key_value(key, value, indent) }.join("\n")
end

def emit_sequence_item(item, indent)
  pad = " " * indent
  case item
  when Hash
    keys = item.keys
    return "#{pad}- {}" if keys.empty?

    first = keys.first
    first_value = item[first]
    first_rendered = emit_key_value(first, first_value, indent + 2).sub(/^#{' ' * (indent + 2)}/, "")
    rest = keys.drop(1).map { |key| emit_key_value(key, item[key], indent + 2) }
    (["#{pad}- #{first_rendered}"] + rest).join("\n")
  when Array
    return "#{pad}- []" if item.empty?

    first = item.first
    rendered_first = emit_sequence_item(first, indent + 2).sub(/^#{' ' * (indent + 2)}/, "")
    rest = item.drop(1).map { |child| emit_sequence_item(child, indent + 2) }
    (["#{pad}- #{rendered_first}"] + rest).join("\n")
  else
    "#{pad}- #{quote_scalar(item)}"
  end
end

def emit_sequence(array, indent = 0)
  array.map { |item| emit_sequence_item(item, indent) }.join("\n")
end

def emit_document(data)
  "#{emit_mapping(data)}\n"
end

def load_yaml_mapping(path)
  data = YAML.load_file(path.to_s)
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

write_rules = ARGV.include?("--write-rules")
rule_paths = RULES_DIR.glob("*.yaml").sort
all_modes = []

rule_paths.each do |path|
  modes = load_rule_modes(path)
  write_rule_file(path, modes) if write_rules
  all_modes.concat(modes)
end

ALL_AGENTS.write(emit_document({ "customModes" => all_modes, "source" => "project" }), encoding: "UTF-8")
puts "generated #{ALL_AGENTS.relative_path_from(ROOT)} with #{all_modes.length} custom modes"
puts "normalized #{rule_paths.length} rule files" if write_rules
