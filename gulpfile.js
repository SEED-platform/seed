/*global require*/
'use strict';

var gulp = require('gulp');
var $ = require('gulp-load-plugins')();

var conf = {
  jsPattern: ['./seed/landing/static/**/*.js', './seed/static/seed/**/*.js'],
  errorHandler: function (title) {
    return function (err) {
      $.util.log($.util.colors.red('[' + title + ']'), err.toString());
      if (this && this.hasOwnProperty('emit')) this.emit('end');
    };
  }
};

var eslint = function (fix) {
  fix = !!fix;
  return gulp.src(conf.jsPattern, {base: '.'})
    .pipe($.eslint({fix: fix}))
    .pipe($.eslint.format())
    .pipe(fix ? gulp.dest('.') : $.util.noop());
};

gulp.task('lint', function () {
  return eslint();
});

gulp.task('lint:fix', function () {
  return eslint(true);
});

// Default task
gulp.task('default', ['lint']);
