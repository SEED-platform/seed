/**
 * :copyright: (c) 2014 Building Energy Inc
 */
// create dummy angularJS app to attach filter(s)
var searchTestApp = angular.module(
    'searchTestApp', ['BE.seed.service.search', 'BE.seed.utilities']
);

describe('The search_service service', function() {
    var saas, httpBackend;
    var test_url = '';
    var mock_spinner_utility;

    beforeEach(function () {
        module('searchTestApp');
        inject(function (search_service, $httpBackend, $q, spinner_utility) {
            saas = search_service;
            httpBackend = $httpBackend;
            httpBackend.when('POST', test_url).respond('ok');
            mock_spinner_utility = spinner_utility;

            spyOn(mock_spinner_utility, 'show')
                .andCallFake(function(){
                    //do nothing
                });
            spyOn(mock_spinner_utility, 'hide')
                .andCallFake(function(){
                    //do nothing
                });
        });
    });


    /**
     * sanitize_params tests
     */
    it('removes null and undefined values from filter_params', function () {
        // arrange
        saas.filter_params = {
          'National Median Site Energy Use__gte': 4,
          'National Median Site Energy Use__lte': null,
          'National Median Source EUI__gte': undefined
        };

        // act
        saas.sanitize_params();

        // assert
        expect(saas.filter_params).toEqual({'National Median Site Energy Use__gte': 4});
    });

    /**
     * search_buildings tests
     */
    it('has sane defaults', function() {
        expect(saas.url).toEqual('');
        expect(saas.error_message).toEqual('');
        expect(saas.alert).toEqual(false);
        expect(saas.buildings).toEqual([]);
        expect(saas.current_page).toEqual(1);
        expect(saas.number_per_page).toEqual(10);
        expect(saas.order_by).toEqual('');
        expect(saas.sort_column).toEqual('tax_lot_id');
        expect(saas.sort_reverse).toEqual(false);
        expect(saas.select_all_checkbox).toEqual(false);
        expect(saas.prev_page_disabled).toEqual(true);
        expect(saas.next_page_disabled).toEqual(true);
        expect(saas.num_pages()).toEqual(0);
        expect(saas.query).toEqual('');
        expect(saas.showing).toEqual({
            start: 1,
            end: 0
        });
    });

    it('search_buildings uses the argument `query`', function() {
        saas.query = 'hotels';
        saas.search_buildings('not hotels');

        expect(saas.query).toEqual('not hotels');
    });

    it('filter search resets the current page', function() {
        // arrange
        saas.current_page = 22;
        spyOn(saas, 'search_buildings');

        // act
        saas.filter_search();

        // assert
        expect(saas.current_page).toEqual(1);
        expect(saas.search_buildings).toHaveBeenCalled();
    });


    it('search_buildings function will default to its query if' +
        ' no query is passed as an argument', function() {
        saas.query = 'hotels';
        saas.search_buildings();

        expect(saas.query).toEqual('hotels');
    });

    it('search_buildings hits the set url', function() {
        test_url = '/my-search-url';
        saas.url = test_url;
        saas.search_buildings();
        httpBackend.expectPOST(test_url);
        httpBackend.flush();
    });

    it('search_buildings POSTs the query data as `q`', function() {
        // arrange
        test_url = 'https://mytest.com';
        saas.url = test_url;
        saas.query = 'hotel chains';
        saas.number_per_page = 25;
        saas.order_by = 'gross_floor_area';
        saas.sort_reverse = true;
        saas.filter_params = {
            project: '2012 data'
        };

        // act
        saas.search_buildings();

        // assert
        httpBackend.expectPOST(test_url,
            {
                q: 'hotel chains',
                number_per_page: 25,
                order_by: 'gross_floor_area',
                sort_reverse: true,
                filter_params: {
                    project: '2012 data'
                },
                page:1
            }
        ).respond(201, '');
        // httpBackend.flush();
    });
    it('search_buildings updates its `buildings` model', function() {
        // arrange
        test_url = 'https://mytest.com';
        saas.url = test_url;
        saas.query = 'hotel chains';
        saas.number_per_page = 25;
        saas.order_by = 'gross_floor_area';
        saas.sort_reverse = true;
        saas.filter_params = {
            project: '2012 data'
        };

        // act
        saas.search_buildings();

        // assert
        httpBackend.expectPOST(test_url,
            {
                q: 'hotel chains',
                number_per_page: 25,
                order_by: 'gross_floor_area',
                sort_reverse: true,
                filter_params: {
                    project: '2012 data'
                },
                page:1
            }
        ).respond(201, {buildings: [
            {
                name: 'one',
                id: 1
            },
            {
                name: 'two',
                id: 2
            }
        ]});
        // httpBackend.flush();

        // Needs to wait will search is finished
        setTimeout( function () {
            expect(saas.buildings).toEqual([
                {
                    name: 'one',
                    id: 1,
                    checked: false
                },
                {
                    name: 'two',
                    id: 2,
                    checked: false
                }
            ]);
        },1000);
    });
    it('should clear the error and alert after a successful search',
        function() {
        // arrange
        test_url = 'https://mytest.com';
        saas.url = test_url;
        saas.error_message = 'help';
        saas.alert = true;

        // act
        saas.search_buildings();
        httpBackend.expectPOST(test_url).respond(201, {
            buildings: [
                {
                    name: 'one',
                    id: 1
                },
                {
                    name: 'two',
                    id: 2
                }],
            number_matching_search: 101
            });
        httpBackend.flush();

        // assert
        expect(saas.alert).toEqual(false);
        expect(saas.error_message).toEqual('');
    });

    /**
     * pagination tests
     */
    it('increments the page when the `next` button is clicked',
        function() {
        // arrange
        saas.number_matching_search = 10000;
        saas.number_per_page = 10;
        saas.current_page = 100;
        spyOn(saas, 'search_buildings');
        // act
        saas.next_page();

        // assert
        expect(saas.current_page).toEqual(101);
        expect(saas.search_buildings).toHaveBeenCalled();
        expect(saas.search_buildings.callCount).toEqual(1);

    });
    it('doesn\'t increment past the last page when the `next` button is' +
        ' clicked', function() {
        // arrange
        saas.number_matching_search = 20;
        saas.number_per_page = 10;
        saas.current_page = 2;
        spyOn(saas, 'search_buildings');
        // act
        saas.next_page();

        // assert
        expect(saas.current_page).toEqual(2);
        expect(saas.search_buildings).toHaveBeenCalled();
        expect(saas.search_buildings.callCount).toEqual(1);

    });
    it('decrements the page when the `previous` button is clicked',
        function() {
        // arrange
        saas.number_matching_search = 10000;
        saas.number_per_page = 10;
        saas.current_page = 100;
        spyOn(saas, 'search_buildings');
        // act
        saas.prev_page();

        // assert
        expect(saas.current_page).toEqual(99);
        expect(saas.search_buildings).toHaveBeenCalled();
    });
    it('does not decrement below the first page when the `previous` button' +
        ' is clicked', function() {
        // arrange
        saas.num_pages = 1;
        saas.number_per_page = 10;
        saas.current_page = 1;
        spyOn(saas, 'search_buildings');
        // act
        saas.prev_page();

        // assert
        expect(saas.current_page).toEqual(1);
        expect(saas.search_buildings).toHaveBeenCalled();
    });
    it('fetches more or less results per page when a user selects an option' +
        ' from the number per page select',
        function() {
        // arrange
        saas.number_per_page_options_model = 50;
        spyOn(saas, 'search_buildings');
        // act
        saas.update_number_per_page();

        // assert
        expect(saas.number_per_page).toEqual(50);
        expect(saas.search_buildings).toHaveBeenCalled();
    });
    it('updates the number of results displayed text after a successful '+
        'search', function() {
        // standard case
        // page 2 of 3 with 10/page, so should display 11 of 20
        // arrange
        saas.current_page = 2;
        saas.number_per_page = 10;
        saas.number_matching_search = 30;
        spyOn(saas, 'search_buildings');
        // act
        saas.update_start_end_paging();

        // assert
        expect(saas.showing.start).toEqual(11);
        expect(saas.showing.end).toEqual(20);
        expect(saas.search_buildings).not.toHaveBeenCalled();
    });
    it('displays the number matching the query if on the last page of results',
        function() {
        // standard case
        // page 4 of 4 with 10/page and 34 results, so should display 31 of 34
        // arrange
        saas.current_page = 4;
        saas.number_per_page = 10;
        saas.number_matching_search = 34;
        spyOn(saas, 'search_buildings');
        // act
        saas.update_start_end_paging();

        // assert
        expect(saas.showing.start).toEqual(31);
        expect(saas.showing.end).toEqual(34);
    });
    it('should call update_start_end_paging after a successful search',
        function() {
        // arrange
        spyOn(saas, 'update_start_end_paging');
        test_url = 'https://mytest.com';
        saas.url = test_url;

        // act
        saas.search_buildings();
        httpBackend.expectPOST(test_url).respond(201, {buildings: [
            {
                name: 'one',
                id: 1
            },
            {
                name: 'two',
                id: 2
            }
        ]});
        httpBackend.flush();

        // assert
        expect(saas.update_start_end_paging).toHaveBeenCalled();
    });
    it('should call update_buttons after a successful search',
        function() {
        // arrange
        spyOn(saas, 'update_buttons');
        test_url = 'https://mytest.com';
        saas.url = test_url;

        // act
        saas.search_buildings();
        httpBackend.expectPOST(test_url).respond(201, {buildings: [
            {
                name: 'one',
                id: 1
            },
            {
                name: 'two',
                id: 2
            }
        ]});
        httpBackend.flush();

        // assert
        expect(saas.update_buttons).toHaveBeenCalled();
    });
    it('should disable prev paging buttons at the first page',
        function() {
        // arrange
        saas.current_page = 1;
        saas.number_matching_search = 50;
        saas.number_per_page = 10;

        // act
        saas.update_buttons();

        // assert
        expect(saas.prev_page_disabled).toEqual(true);
        expect(saas.next_page_disabled).toEqual(false);
    });
    it('should disable next paging buttons at the last page',
        function() {
        // arrange
        saas.current_page = 5;
        saas.number_per_page = 10;
        saas.number_matching_search = 50;

        // act
        saas.update_buttons();

        // assert
        expect(saas.prev_page_disabled).toEqual(false);
        expect(saas.next_page_disabled).toEqual(true);
    });
    it('should calculate the number of pages after a successful search',
        function() {
        // arrange
        test_url = 'https://mytest.com';
        saas.url = test_url;

        // act
        saas.search_buildings();
        httpBackend.expectPOST(test_url).respond(201, {
            buildings: [
                {
                    name: 'one',
                    id: 1
                },
                {
                    name: 'two',
                    id: 2
                }],
            number_matching_search: 101
            });
        httpBackend.flush();

        // assert
        expect(saas.number_matching_search).toEqual(101);
        expect(saas.num_pages()).toEqual(11);
    });

    /**
     * checkbox logic tests
     */
    it('should select or unselect all the viewed results when the select all' +
        ' checkbox is checked or unchecked', function() {
        // arrange
        saas.selected_buildings = [1, 2, 3];
        saas.select_all_checkbox = true;
        saas.buildings = [
            {
                checked: false
            },
            {
                checked: true
            }
        ];
        spyOn(saas, 'select_or_deselect_all_buildings').andCallThrough();

        // act
        saas.select_all_changed();

        // assert
        expect(saas.selected_buildings).toEqual([]);
        expect(saas.buildings).toEqual([
                {
                    checked: true
                },
                {
                    checked: true
                }
            ]);
        expect(saas.select_or_deselect_all_buildings).toHaveBeenCalled();
    });
    it('should call select_or_deselect_all_buildings after a search',
        function() {
        // arrange
        spyOn(saas, 'select_or_deselect_all_buildings');
        test_url = 'https://mytest.com';
        saas.url = test_url;

        // act
        saas.search_buildings();
        httpBackend.expectPOST(test_url).respond(201, {buildings: [
            {
                name: 'one',
                id: 1
            },
            {
                name: 'two',
                id: 2
            }
        ]});
        httpBackend.flush();

        // assert
        expect(saas.select_or_deselect_all_buildings).toHaveBeenCalled();
    });
    it('should add a building to the selected list when checked',
        function() {
        // arrange
        var building = {
            id: 5,
            checked: true
        };

        // act
        saas.add_remove_to_list(building);

        // assert
        expect(saas.selected_buildings).toEqual([5]);
    });
    it('should add a building to the selected list when unchecked and the ' +
        'select all checkbox is checked', function() {
        // arrange
        var building = {
            id: 5,
            checked: false
        };
        saas.select_all_checkbox = true;

        // act
        saas.add_remove_to_list(building);

        // assert
        expect(saas.selected_buildings).toEqual([5]);
    });
    it('should remove a building to the selected list when unchecked',
        function() {
        // arrange
        var building = {
            id: 5,
            checked: false
        };
        saas.selected_buildings = [5, 6, 7];
        saas.select_all_checkbox = false;

        // act
        saas.add_remove_to_list(building);

        // assert
        expect(saas.selected_buildings).toEqual([6, 7]);
    });
    it('should remove a building to the selected list when checked if the ' +
        'select all checkbox is checked', function() {
        // arrange
        var building = {
            id: 5,
            checked: true
        };
        saas.selected_buildings = [5, 6, 7];
        saas.select_all_checkbox = true;

        // act
        saas.add_remove_to_list(building);

        // assert
        expect(saas.selected_buildings).toEqual([6, 7]);
    });
    it('should call load_state_from_selected_buildings after a successful ' +
        'search', function() {
        // arrange
        spyOn(saas, 'load_state_from_selected_buildings').andCallThrough();
        test_url = 'https://mytest.com';
        saas.url = test_url;

        // act
        saas.search_buildings();
        httpBackend.expectPOST(test_url).respond(201, {buildings: [
            {
                name: 'one',
                id: 1,
                checked: false
            },
            {
                name: 'two',
                id: 2,
                checked: false
            }
        ]});
        httpBackend.flush();

        // assert
        expect(saas.load_state_from_selected_buildings).toHaveBeenCalled();
    });
    it('should call update_results after a successful ' +
        'search', function() {
        // arrange
        var select_or_deselect_all_buildings_time,
            load_state_from_selected_buildings_time;
        spyOn(saas, 'update_results').andCallThrough();
        spyOn(saas, 'select_or_deselect_all_buildings')
            .andCallFake(function() {
                select_or_deselect_all_buildings_time = new Date();
            }
        );
        spyOn(saas, 'load_state_from_selected_buildings')
            .andCallFake(function() {
                // wait for a sec, otherwise both have the same timestamp
                for(var y=0;y<100000;y++){
                    var x = new Date();
                    x = x+y;
                }
                load_state_from_selected_buildings_time = new Date();
            }
        );
        test_url = 'https://mytest.com';
        saas.url = test_url;

        // act
        saas.search_buildings();
        httpBackend.expectPOST(test_url).respond(201, {buildings: [
            {
                name: 'one',
                id: 1,
                checked: false
            },
            {
                name: 'two',
                id: 2,
                checked: false
            }
        ]});
        httpBackend.flush();

        // assert
        expect(saas.update_results).toHaveBeenCalled();
        expect(select_or_deselect_all_buildings_time <
               load_state_from_selected_buildings_time).toBe(true);
    });
    it('check selected buildings successful', function() {
        // arrange
        saas.selected_buildings = [2];
        saas.buildings = [
            {
                name: 'one',
                id: 1
            },
            {
                name: 'two',
                id: 2
            }
        ];

        // act
        saas.load_state_from_selected_buildings();

        // assert
        expect(saas.buildings[1]).toEqual({
            name: 'two',
            id: 2,
            checked: true
        });
    });
    it('should generate columns', function() {
        // arrange
        var all_columns, column_headers, columns;
        all_columns = [
            {
                sort_column: 'name'
            },
            {
                sort_column: 'id'
            }
        ];
        column_headers = ['id'];
        saas.sort_column = 'something else';
        saas.update_results({});
        // act
        columns = saas.generate_columns(
            all_columns, column_headers, saas.column_prototype
        );

        // assert that columns are extended off the prototype and only have
        // "id"
        expect(columns.length).toEqual(1);
        expect(columns[0].sort_column).toEqual('id');
        expect(columns[0].is_unsorted()).toEqual(true);
        saas.sort_column = 'id';
        expect(columns[0].is_unsorted()).toEqual(false);
    });
});
