Feature: dataset

Scenario: Delete dataset
    Given I am logged in
        And I have a dataset
    When I visit the dataset page
        And I delete a dataset
    Then I should see no datasets
