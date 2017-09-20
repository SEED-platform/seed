# Release Instructions

To perform a release make sure to do the following.

1. Update the `package.json` file with the most recent version number
1. Run the `docs/scripts/change_log.rb` script and add the changes to the CHANGELOG.md file for the range of time between last release and this release
   
   
    ruby docs/scripts/change_log.rb --token GITHUB_API_TOKEN --start-date 2017-07-01 --end-date 2017-09-30 

1. Paste the results (except the Accepted Pull Requests) into the CHANGELOG.md

