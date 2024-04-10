/**
 * SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
 * See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
 */
const BEHome = window.BEHome ?? {};
BEHome.actions = BEHome.actions ?? {};
BEHome.handlers = BEHome.handlers ?? {};
BEHome.util = BEHome.util ?? {};

BEHome.actions.hide_choose_your_path = () => {
  $('.choose_your_path').hide();
};
BEHome.actions.show_choose_your_path = () => {
  $('.choose_your_path').show();
};
BEHome.actions.hide_all_forms = () => {
  $('.enter_invite_code_form').hide();
  $('.current_account_link').hide();
};
BEHome.actions.show_request_form = () => {
  BEHome.actions.hide_choose_your_path();
  BEHome.actions.hide_all_forms();
};
BEHome.actions.show_signup_form = () => {
  BEHome.actions.hide_choose_your_path();
  BEHome.actions.hide_all_forms();
  $('.enter_invite_code_form').show();
};
BEHome.actions.show_login_form = () => {
  BEHome.actions.hide_choose_your_path();
  BEHome.actions.hide_all_forms();
  $('.current_account_link').show();
};
BEHome.actions.show_unsupported_browser_message = () => {
  $('.browser_unsupported').show();
};
BEHome.actions.hide_login_form = () => {
  $('.form_title').hide();
};
BEHome.handlers.handle_signup_choice_button = () => {
  BEHome.actions.show_signup_form();
  return false;
};
BEHome.handlers.handle_request_invite_button = () => {
  BEHome.actions.show_request_form();
  return false;
};
BEHome.handlers.handle_login_button = () => {
  BEHome.actions.show_login_form();
  return false;
};
BEHome.handlers.handle_cancel_button = () => {
  BEHome.actions.hide_all_forms();
  BEHome.actions.show_choose_your_path();
  return false;
};
BEHome.util.bind_all_handlers = () => {
  $('.btn_landing_landing.invite').on('click', BEHome.handlers.handle_signup_choice_button);
  $('.btn_landing_landing.request').on('click', BEHome.handlers.handle_request_invite_button);
  $('.btn_landing_landing.login').on('click', BEHome.handlers.handle_login_button);
  $('.already_signed_up').on('click', BEHome.handlers.handle_login_button);
  $('.cancel_btn').on('click', BEHome.handlers.handle_cancel_button);
};
$(() => {
  BEHome.actions.hide_all_forms();
  BEHome.util.bind_all_handlers();
});
