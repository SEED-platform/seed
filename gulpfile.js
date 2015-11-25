'use strict';

var gulp = require('gulp');
var gutil = require('gulp-util');
var jshint = require('gulp-jshint');
var fixmyjs = require("gulp-fixmyjs");
var sourcemaps = require('gulp-sourcemaps');
var sass = require('gulp-sass');
var autoprefixer = require('gulp-autoprefixer');
var csso = require('gulp-csso');
require('es6-promise').polyfill();

var conf = {
  jshintPattern: ['./seed/landing/static/**/*.js', './seed/static/seed/**/*.js'],
  sassPattern: ['./seed/landing/static/landing/scss/**/*.scss', './seed/static/seed/scss/**/*.scss'],
  autoprefixerOptions: {
    browsers: ['last 3 versions', 'ie >= 8'],
    cascade: false
  },
  errorHandler: function (title) {
    return function (err) {
      gutil.log(gutil.colors.red('[' + title + ']'), err.toString());
      if (this && this.hasOwnProperty('emit')) this.emit('end');
    };
  }
};

// Run jshint
gulp.task('jshint', function () {
  return gulp.src(conf.jshintPattern)
    .pipe(jshint())
    .pipe(jshint.reporter('jshint-stylish'));
});
gulp.task('jshint:fix', function () {
  return gulp.src(conf.jshintPattern, {
    base: '.'
  }).pipe(fixmyjs())
    .pipe(gulp.dest('.'));
});

// Compile SCSS
gulp.task('sass', function () {
  return gulp.src(conf.sassPattern)
    .pipe(sourcemaps.init())
    .pipe(sass({noCache: true})).on('error', conf.errorHandler('Sass'))
    .pipe(autoprefixer(conf.autoprefixerOptions)).on('error', conf.errorHandler('Autoprefixer'))
    .pipe(csso())
    .pipe(sourcemaps.write('.'))
    .pipe(gulp.dest('./seed/static/seed/css'));
});

// Monitor SCSS files and recompile on change
gulp.task('watch', ['sass'], function () {
  gulp.watch(conf.sassPattern, ['sass']);
});

// Default task
gulp.task('default', ['watch']);
