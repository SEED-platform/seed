Feature: Landing page

Scenario: There is a login
    Given I visit the landing page
    Then I should see the login prompt


Scenario: I log in
    Given I visit the landing page
    And I am an exising user
    When I log into the system
    Then I should be redirected to the home page


Scenario: I don't log in
    Given I visit the landing page
    And I am an exising user
    When I try to log into the system with the wrong password
    Then I should see the text "Username and/or password were invalid."
