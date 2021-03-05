var BEHome = BEHome || {};
BEHome.actions = BEHome.actions || {};
BEHome.handlers = BEHome.handlers || {};
BEHome.util = BEHome.util || {};

BEHome.actions.hide_choose_your_path = function () {
  $('.choose_your_path').hide();
};
BEHome.actions.show_choose_your_path = function () {
  $('.choose_your_path').show();
};
BEHome.actions.hide_all_forms = function () {
  $('.enter_invite_code_form').hide();
  $('.current_account_link').hide();
};
BEHome.actions.show_request_form = function () {
  BEHome.actions.hide_choose_your_path();
  BEHome.actions.hide_all_forms();
};
BEHome.actions.show_signup_form = function () {
  BEHome.actions.hide_choose_your_path();
  BEHome.actions.hide_all_forms();
  $('.enter_invite_code_form').show();
};
BEHome.actions.show_login_form = function () {
  BEHome.actions.hide_choose_your_path();
  BEHome.actions.hide_all_forms();
  $('.current_account_link').show();
};
BEHome.actions.check_unsupported_browser = function () {
  // var version=parseInt($.browser.version, 10);
  // if(($.browser.msie&&version<9)||($.browser.mozila&&version<3)||($.browser.webkit&&version<200)) {
  //     BEHome.actions.show_unsupported_browser_message();
  //     BEHome.actions.hide_login_form();
  // }
};
BEHome.actions.show_unsupported_browser_message = function () {
  $('.browser_unsupported').show();
};
BEHome.actions.hide_login_form = function () {
  $('.form_title').hide();
};
BEHome.handlers.handle_signup_choice_button = function () {
  BEHome.actions.show_signup_form();
  return false;
};
BEHome.handlers.handle_request_invite_button = function () {
  BEHome.actions.show_request_form();
  return false;
};
BEHome.handlers.handle_login_button = function () {
  BEHome.actions.show_login_form();
  BEHome.actions.check_unsupported_browser();
  return false;
};
BEHome.handlers.handle_cancel_button = function () {
  BEHome.actions.hide_all_forms();
  BEHome.actions.show_choose_your_path();
  return false;
};
BEHome.util.bind_all_handlers = function () {
  $('.btn_landing_landing.invite').on('click', BEHome.handlers.handle_signup_choice_button);
  $('.btn_landing_landing.request').on('click', BEHome.handlers.handle_request_invite_button);
  $('.btn_landing_landing.login').on('click', BEHome.handlers.handle_login_button);
  $('.already_signed_up').on('click', BEHome.handlers.handle_login_button);
  $('.cancel_btn').on('click', BEHome.handlers.handle_cancel_button);
};
$(function () {
  BEHome.actions.hide_all_forms();
  BEHome.util.bind_all_handlers();
});

