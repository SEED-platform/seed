/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
angular.module('SEED.controller.data_report_editor_modal', [])
    .controller('data_report_editor_modal_controller', [
        '$scope',
        '$state',
        '$stateParams',
        '$uibModalInstance',
        'urls',
        'Notification',
        'ah_service',
        'data_report_service',
        'access_level_tree',
        'area_columns',
        'auth_payload',
        'data_report',
        'cycles',
        'eui_columns',
        'organization',
        'write_permission',
        // eslint-disable-next-line func-names
        function (
            $scope,
            $state,
            $stateParams,
            $uibModalInstance,
            urls,
            Notification,
            ah_service,
            data_report_service,
            access_level_tree,
            area_columns,
            auth_payload,
            data_report,
            cycles,
            eui_columns,
            organization,
            write_permission
        ) {
            $scope.urls = urls;
            $scope.auth = auth_payload.auth;
            $scope.organization = organization;
            $scope.write_permission = write_permission;
            $scope.data_report = data_report || {};
            $scope.access_level_tree = access_level_tree.access_level_tree;
            $scope.level_names = access_level_tree.access_level_names.map((level, i) => ({
                index: i,
                name: level
            }));
            $scope.cycles = cycles;
            $scope.area_columns = area_columns;
            $scope.eui_columns = eui_columns;
            // allow "none" as an option
            if (!eui_columns.find((col) => col.id === null && col.displayName === '')) {
                $scope.eui_columns.unshift({ id: null, displayName: '' });
            }
            $scope.valid = false;

            $scope.data_report_types = [
                {display_name: "Standard", type: "standard"},
                {display_name: "Transaction", type: "transaction"}
            ]

            const sort_data_reports = (data_reports) => data_reports.sort((a, b) => (a.name.toLowerCase() < b.name.toLowerCase() ? -1 : 1));
            const get_data_reports = () => {
                data_report_service.get_data_reports().then((result) => {
                    $scope.data_reports = result.status === 'success' ? sort_data_reports(result.data_reports) : [];
                });
            };
            get_data_reports();

            $scope.$watch('data_report', (cur, old) => {
                $scope.data_report_changed = cur !== old;
            }, true);

            const access_level_instances_by_depth = ah_service.calculate_access_level_instances_by_depth($scope.access_level_tree);

            $scope.change_selected_level_index = () => {
                const new_level_instance_depth = parseInt($scope.data_report.level_name_index, 10) + 1;
                $scope.potential_level_instances = access_level_instances_by_depth[new_level_instance_depth];
            };
            $scope.change_selected_level_index();

            $scope.set_data_report = (data_report) => {
                $scope.data_report = data_report;
                if (_.isEmpty($scope.data_report.goals)) $scope.data_report.goals = [{}]
                $scope.change_selected_level_index();
            };

            $scope.save_data_report = () => {
                $scope.data_report_changed = false;
                const data_report_fn = $scope.data_report.id ? data_report_service.update_data_report : data_report_service.create_data_report;
                // if new data_report, assign org id
                $scope.data_report.organization = $scope.data_report.organization || $scope.organization.id;
                
                data_report_fn($scope.data_report).then((result) => {
                    if (result.status === 'success') {
                        Notification.success({ message: 'Data Report saved', delay: 5000 });
                        $scope.errors = null;
                        $scope.data_report.id = $scope.data_report.id || result.data.id;
                        get_data_reports();
                        $scope.set_data_report($scope.data_report);
                    } else {
                        $scope.errors = [`Unexpected response status: ${result.status}`];
                        const result_errors = 'errors' in result.data ? result.data.errors : result.data;
                        if (result_errors instanceof Object) {
                            for (const key in result_errors) {
                                const key_string = key === 'non_field_errors' ? 'Error' : key;
                                $scope.errors.push(`${key_string}: ${JSON.stringify(result_errors[key])}`);
                            }
                        } else {
                            $scope.errors = $scope.errors.push(result_errors);
                        }
                    }
                })
                    .catch((response) => {
                        const message = response.data.message || 'Unexpected Error';
                        Notification.error(message);
                    });
            };

            $scope.delete_data_report = (data_report_id) => {
                const data_report = $scope.data_reports.find((data_report) => data_report.id === data_report_id);
                if (!data_report) return Notification.warning({ message: 'Unexpected Error', delay: 5000 });

                if (!confirm(`Are you sure you want to delete Data Report "${data_report.name}"`)) return;

                data_report_service.delete_data_report(data_report_id).then((response) => {
                    if (response.status === 204) {
                        Notification.success({ message: 'Data Report deleted successfully', delay: 5000 });
                    } else {
                        Notification.warning({ message: 'Unexpected Error', delay: 5000 });
                    }
                    get_data_reports();
                    if (data_report_id === $scope.data_report.id) {
                        $scope.data_report = null;
                    }
                });
            };

            $scope.new_data_report = () => {
                $scope.data_report = {
                    type: "standard",
                    baseline_cycle: cycles.at(0).id,
                    current_cycle: cycles.at(-1).id,
                    level_name_index: $scope.level_names[0].index,
                    access_level_instance: $scope.potential_level_instances[0].id,
                    target_percentage: 20,
                    goals: [{}]
                };
            };

            $scope.add_goal = () => $scope.data_report.goals.push({});
            $scope.remove_goal = (index) => $scope.data_report.goals.splice(index);

            $scope.close = () => {
                const data_report_name = $scope.data_report ? $scope.data_report.name : null;
                $uibModalInstance.close(data_report_name);
            };
        }]);
