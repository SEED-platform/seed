/**
 * SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
// Superusers see every organization but can only use the ones they are a member of, so picking another one offers to
// add them as an owner instead of failing to switch (GitHub issue #4618).
describe('controller: join_organization_modal_controller', () => {
  let $controller;
  let $rootScope;
  let $q;
  let organization_service;
  let user_service;
  let modal_instance;
  const organization = { id: 7, name: 'Other Org', user_role: null };

  beforeEach(() => {
    module('SEED');
    inject((_$httpBackend_) => {
      _$httpBackend_.whenGET(/^\/static\/seed\/locales\/.*\.json/).respond(200, {});
    });
    inject((_$controller_, _$rootScope_, _$q_, _organization_service_, _user_service_) => {
      $controller = _$controller_;
      $rootScope = _$rootScope_;
      $q = _$q_;
      organization_service = _organization_service_;
      user_service = _user_service_;
    });
    spyOn(user_service, 'get_user_id').and.returnValue($q.resolve(3));
    modal_instance = jasmine.createSpyObj('$uibModalInstance', ['close', 'dismiss']);
  });

  const create_controller = () => {
    const $scope = $rootScope.$new();
    $controller('join_organization_modal_controller', {
      $scope,
      $uibModalInstance: modal_instance,
      organization
    });
    return $scope;
  };

  it('adds the current user to the organization and closes', () => {
    spyOn(organization_service, 'add_user_to_org').and.returnValue($q.resolve({ status: 'success' }));
    const $scope = create_controller();

    $scope.join();
    $rootScope.$digest();

    expect(organization_service.add_user_to_org).toHaveBeenCalledWith({ organization: { org_id: 7 }, user: { user_id: 3 } });
    expect(modal_instance.close).toHaveBeenCalled();
    expect($scope.error_message).toBeNull();
  });

  it('shows the error and stays open when adding fails', () => {
    spyOn(organization_service, 'add_user_to_org').and.returnValue($q.reject({ data: { message: 'Nope' } }));
    const $scope = create_controller();

    $scope.join();
    $rootScope.$digest();

    expect(modal_instance.close).not.toHaveBeenCalled();
    expect($scope.error_message).toBe('Nope');
    expect($scope.joining).toBeFalse();
  });

  it('dismisses on cancel without adding', () => {
    spyOn(organization_service, 'add_user_to_org');
    const $scope = create_controller();

    $scope.cancel();

    expect(modal_instance.dismiss).toHaveBeenCalled();
    expect(organization_service.add_user_to_org).not.toHaveBeenCalled();
  });
});

describe('controller: menu_controller set_user_org', () => {
  let $rootScope;
  let $q;
  let $uibModal;
  let $state;
  let user_service;
  let menu_scope;
  let original_seed;

  // set_user_org is async and awaits $q promises, so alternate digests and microtasks until it finishes
  const flush = async () => {
    for (let i = 0; i < 5; i++) {
      $rootScope.$digest();
      // eslint-disable-next-line no-await-in-loop
      await Promise.resolve();
    }
  };

  beforeEach(() => {
    // logged out, so the menu doesn't load organizations on startup
    original_seed = window.SEED;
    window.SEED = { ...window.SEED, username: '', deployment: '' };
    module('SEED');
    inject((_$httpBackend_) => {
      _$httpBackend_.whenGET(/^\/static\/seed\/locales\/.*\.json/).respond(200, {});
    });
    inject(($controller, _$rootScope_, _$q_, _$uibModal_, _$state_, _user_service_) => {
      $rootScope = _$rootScope_;
      $q = _$q_;
      $uibModal = _$uibModal_;
      $state = _$state_;
      user_service = _user_service_;
      menu_scope = $rootScope.$new();
      $controller('menu_controller', { $scope: menu_scope });
    });
    spyOn(user_service, 'set_organization').and.returnValue($q.resolve());
    spyOn($state, 'reload');
  });

  afterEach(() => {
    window.SEED = original_seed;
  });

  it('switches to an organization the user is a member of without asking', async () => {
    spyOn($uibModal, 'open');

    menu_scope.set_user_org({ id: 5, name: 'My Org', user_role: 'member' });
    await flush();

    expect($uibModal.open).not.toHaveBeenCalled();
    expect(user_service.set_organization).toHaveBeenCalledWith({ id: 5, name: 'My Org', user_role: 'member' });
    expect($state.reload).toHaveBeenCalled();
  });

  it('offers to join an organization the superuser is not a member of, then switches as an owner', async () => {
    spyOn($uibModal, 'open').and.returnValue({ result: $q.resolve() });

    menu_scope.set_user_org({ id: 7, name: 'Other Org', user_role: null });
    await flush();

    expect($uibModal.open).toHaveBeenCalledWith(jasmine.objectContaining({ controller: 'join_organization_modal_controller' }));
    expect(user_service.set_organization).toHaveBeenCalledWith({ id: 7, name: 'Other Org', user_role: 'owner' });
    expect($state.reload).toHaveBeenCalled();
  });

  it('stays on the current organization when the superuser declines to join', async () => {
    spyOn($uibModal, 'open').and.returnValue({ result: $q.reject('cancel') });

    menu_scope.set_user_org({ id: 7, name: 'Other Org', user_role: null });
    await flush();

    expect(user_service.set_organization).not.toHaveBeenCalled();
    expect($state.reload).not.toHaveBeenCalled();
  });
});
