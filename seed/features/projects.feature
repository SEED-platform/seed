Feature: Projects

Scenario: List projects
    Given I am logged in
    And I have a project
    When I visit the projects page
    Then I should see my projects
