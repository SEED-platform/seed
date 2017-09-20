require 'github_api'
require 'date'
require 'yaml'
require 'optparse'
require 'optparse/date'
require 'pp'

# Instructions:
#   Get a token from github's settings (https://github.com/settings/tokens)
#
# Example:
#   ruby change_log.rb -t abcdefghijklmnopqrstuvwxyz -s 2017-09-06
#

options = {}
OptionParser.new do |opts|
  opts.banner = "Usage: change_log.rb [options]"

  # defaults, go back 90 days
  options[:start_date] = Date.today - 90
  options[:end_date] = Date.today

  opts.on("-s", "--start-date [DATE]", Date, "Start of data (e.g. 2017-09-06)") do |v|
    options[:start_date] = v
  end
  opts.on("-e", "--end-date [DATE]", Date, "End of data (e.g. 2017-09-13)") do |v|
    options[:end_date] = v
  end
  opts.on("-t", "--token [String]", String, "Github API Token") do |v|
    options[:token] = v
  end
end.parse!

# Convert dates to time objects
options[:start_date] = Time.parse(options[:start_date].to_s)
options[:end_date] = Time.parse(options[:end_date].to_s)
puts options

### Repository options
repo_owner = 'SEED-Platform'
repo = 'SEED'
# List of users who are part of the core team. Their pull requests will not appear as 'external collaborator'
internal_users = ['nllong', 'axelstudios', 'Myoldmopar', 'maronnax']

github = Github.new
if options[:token]
  puts "Using github token"
  token = options[:token]
  github = Github.new oauth_token: token
end

total_open_issues = Array.new
total_open_pull_requests = Array.new
new_issues = Array.new
closed_issues = Array.new
accepted_pull_requests = Array.new
accepted_external_pull_requests = Array.new

def get_num(issue)
  issue.html_url.split('/')[-1].to_i
end

def get_issue_num(issue)
  "\##{get_num(issue)}"
end

def get_html_url(issue)
  issue.html_url
end

def get_title(issue)
  issue.title
end

def print_issue(issue)
  is_feature = false
  issue.labels.each {|label| is_feature = true if label.name == "Feature Request"}

  if is_feature
    "- ![Improved:][improved] [#{get_issue_num(issue)}]( #{get_html_url(issue)} ), #{get_title(issue)}"
  else
    "- ![Fixed:][fixed] [#{get_issue_num(issue)}]( #{get_html_url(issue)} ), #{get_title(issue)}"
  end
end

# Process Open Issues
results = -1
page = 1
while (results != 0)
  resp = github.issues.list user: repo_owner, repo: repo, :sort => 'created', :direction => 'asc',
                            :state => 'open', :per_page => 100, :page => page
  results = resp.length
  resp.env[:body].each do |issue, index|
    created = Time.parse(issue.created_at)
    if !issue.has_key?(:pull_request)
      total_open_issues << issue
      if created >= options[:start_date] && created <= options[:end_date]
        new_issues << issue
      end
    else
      total_open_pull_requests << issue
    end
  end

  page = page + 1
end

# Process Closed Issues
results = -1
page = 1
while (results != 0)
  resp = github.issues.list user: repo_owner, repo: repo, :sort => 'created', :direction => 'asc',
                            :state => 'closed', :per_page => 100, :page => page
  results = resp.length
  resp.env[:body].each do |issue, index|
    created = Time.parse(issue.created_at)
    closed = Time.parse(issue.closed_at)
    if !issue.has_key?(:pull_request)
      if created >= options[:start_date] && created <= options[:end_date]
        new_issues << issue
      end
      if closed >= options[:start_date] && closed <= options[:end_date]
        closed_issues << issue
      end
    elsif closed >= options[:start_date] && closed <= options[:end_date]
      accepted_pull_requests << issue
      unless internal_users.include? issue.user.login
        accepted_external_pull_requests << issue
      end

    end
  end

  page = page + 1
end

closed_issues.sort! {|x, y| get_num(x) <=> get_num(y)}
new_issues.sort! {|x, y| get_num(x) <=> get_num(y)}
accepted_pull_requests.sort! {|x, y| get_num(x) <=> get_num(y)}
total_open_pull_requests.sort! {|x, y| get_num(x) <=> get_num(y)}

puts "Total Open Issues: #{total_open_issues.length}"
puts "Total Open Pull Requests: #{total_open_pull_requests.length}"
puts "\nDate Range: #{options[:start_date].strftime('%m/%d/%y')} - #{options[:end_date].strftime('%m/%d/%y')}:"
puts "\nNew Issues: #{new_issues.length} (" + new_issues.map {|issue| get_issue_num(issue)}.join(', ') + ')'

puts "\nClosed Issues: #{closed_issues.length}"
closed_issues.each {|issue| puts print_issue(issue)}

puts "\nAccepted Pull Requests: #{accepted_pull_requests.length}"
accepted_pull_requests.each {|issue| puts print_issue(issue)}

puts "\nAccepted External Pull Requests: #{accepted_external_pull_requests.length}"
accepted_external_pull_requests.each {|issue| puts print_issue(issue)}

puts "\nAll Open Issues: #{total_open_issues.length} (" + total_open_issues.map {|issue| get_issue_num(issue)}.join(', ') + ')'
