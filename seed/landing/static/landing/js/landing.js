var BEHome = BEHome || {};
BEHome.actions = BEHome.actions || {};
BEHome.handlers = BEHome.handlers || {};
BEHome.util = BEHome.util || {};

BEHome.actions.vertically_center_page = function() {
    var top_and_bottom_margin = $(window).height() - $(".page").height();
    top_and_bottom_margin = (top_and_bottom_margin > 0) ? top_and_bottom_margin / 2 : 0;
    $(".page").css({"margin-top": top_and_bottom_margin});
};

BEHome.actions.hide_choose_your_path = function() {
    $(".choose_your_path").hide();
};
BEHome.actions.show_choose_your_path = function() {
    $(".choose_your_path").show();
};
BEHome.actions.hide_all_forms = function() {
    $("#prefinery_iframe_inline").hide();
    $(".enter_invite_code_form").hide();
    $(".current_account_link").hide();
};


BEHome.actions.show_request_form = function() {
    BEHome.actions.hide_choose_your_path();
    BEHome.actions.hide_all_forms();
    $("#prefinery_iframe_inline").show();
};
BEHome.actions.show_signup_form = function() {
    BEHome.actions.hide_choose_your_path();
    BEHome.actions.hide_all_forms();
    $(".enter_invite_code_form").show();
};
BEHome.actions.show_login_form = function() {
    BEHome.actions.hide_choose_your_path();
    BEHome.actions.hide_all_forms();
    $(".current_account_link").show();
};
BEHome.actions.check_unsupported_browser = function() {
    var version=parseInt($.browser.version,10);
    if(($.browser.msie&&version<9)||($.browser.mozila&&version<3)||($.browser.webkit&&version<200)) {
        BEHome.actions.show_unsupported_browser_message();
        BEHome.actions.hide_login_form();
    }
};
BEHome.actions.show_unsupported_browser_message = function() {
    $(".browser_unsupported").show();
};
BEHome.actions.hide_login_form = function() {
    $(".form_title").hide();
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

BEHome.util.bind_all_handlers = function() {
    $(window).resize(BEHome.actions.vertically_center_page);
    $(".btn_landing_landing.invite").live("click", BEHome.handlers.handle_signup_choice_button);
    $(".btn_landing_landing.request").live("click", BEHome.handlers.handle_request_invite_button);
    $(".btn_landing_landing.login").live("click", BEHome.handlers.handle_login_button);
    $(".already_signed_up").live("click", BEHome.handlers.handle_login_button);
    $(".cancel_btn").live("click", BEHome.handlers.handle_cancel_button);
};

$(function(){
    setTimeout(BEHome.actions.vertically_center_page, 200);
    BEHome.actions.hide_all_forms();
    BEHome.util.bind_all_handlers();
    $('input, textarea').placeholder();
});

