/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
angular.module('BE.seed.service.user', []).factory('user_service', [
  '$http',
  '$q',
  'generated_urls',
  ($http, $q, generated_urls) => {
    const user_factory = {};
    const urls = generated_urls;

    let organization;
    let access_level_instance;
    let user_id;

    /**
     * returns the current organization, set initially by a controller
     *
     * yes this is a global, but otherwise we'll have to use a promise in
     * front of every request that needs this. window.config.initial_org_id is
     * set in base.html via the seed.views.main home view
     *
     * @return {obj} organization
     */
    user_factory.get_organization = () => organization ?? {
      id: window.BE.initial_org_id,
      name: window.BE.initial_org_name,
      user_role: window.BE.initial_org_user_role
    };

    user_factory.get_access_level_instance = () => access_level_instance ?? {
      id: window.BE.access_level_instance_id,
      name: window.BE.access_level_instance_name,
      is_ali_root: window.BE.is_ali_root,
      is_ali_leaf: window.BE.is_ali_leaf
    };

    /**
     * sets the current organization
     * @param {obj} org
     * @return {promise}
     */
    user_factory.set_organization = (org) => {
      organization = org;
      return user_factory.get_user_id().then((this_user_id) => $http
        .put(
          `/api/v3/users/${this_user_id}/default_organization/`,
          {},
          {
            params: { organization_id: org.id }
          }
        )
        .then(({ data }) => {
          access_level_instance = data.user.access_level_instance;
          return data;
        }));
    };

    user_factory.get_users = () => $http.get('/api/v3/users/').then((response) => response.data);

    user_factory.add = (user) => {
      const new_user_details = {
        first_name: user.first_name,
        last_name: user.last_name,
        email: user.email,
        org_name: user.org_name,
        role: user.role,
        access_level_instance_id: user.access_level_instance_id
      };

      const params = {};
      if (!_.isUndefined(user.organization)) {
        params.organization_id = user.organization.org_id;
      }

      return $http.post('/api/v3/users/', new_user_details, { params }).then((response) => response.data);
    };

    /* Is this still needed? */
    user_factory.get_default_columns = () => $http.get(urls.seed.get_default_columns).then((response) => response.data);

    user_factory.get_default_building_detail_columns = () => $http.get(urls.seed.get_default_building_detail_columns).then((response) => response.data);

    user_factory.get_shared_buildings = () => user_factory.get_user_id().then((this_user_id) => $http.get(`/api/v3/users/${this_user_id}/shared_buildings/`).then((response) => response.data));

    /**
     * gets the user's first name, last name, email, and API key if exists
     * @return {obj} object with keys: first_name, last_name, email, api_key
     */
    user_factory.get_user_profile = () => user_factory.get_user_id().then((this_user_id) => $http.get(`/api/v3/users/${this_user_id}/`).then((response) => response.data));

    /**
     * asks the server to generate a new API key
     * @return {obj} object with api_key
     */
    user_factory.generate_api_key = () => user_factory.get_user_id().then((this_user_id) => $http.post(`/api/v3/users/${this_user_id}/generate_api_key/`).then((response) => response.data));

    user_factory.set_default_building_detail_columns = (columns) => $http
      .post(urls.seed.set_default_building_detail_columns, {
        columns
      })
      .then((response) => response.data);

    /**
     * updates the user's PR
     * @param  {obj} user
     */
    user_factory.update_user = (user) => user_factory.get_user_id().then((this_user_id) => $http
      .put(`/api/v3/users/${this_user_id}/`, {
        first_name: user.first_name,
        last_name: user.last_name,
        email: user.email
      })
      .then((response) => response.data));

    /**
     * sets the user's password
     * @param {string} current_password
     * @param {string} password_1
     * @param {string} password_2
     */
    user_factory.set_password = (current_password, password_1, password_2) => user_factory.get_user_id().then((this_user_id) => $http
      .put(`/api/v3/users/${this_user_id}/set_password/`, {
        current_password,
        password_1,
        password_2
      })
      .then((response) => response.data));

    /**
     * gets the current user's id
     */
    user_factory.get_user_id = () => {
      if (_.isUndefined(user_id)) {
        user_id = $http.get('/api/v3/users/current/').then((response) => response.data.pk);
      }
      return user_id;
    };

    return user_factory;
  }
]);
