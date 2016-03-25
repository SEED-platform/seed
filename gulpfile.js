/*global require*/
'use strict';

var gulp = require('gulp');
var $ = require('gulp-load-plugins')();

var conf = {
  jsPattern: ['./seed/landing/static/**/*.js', './seed/static/seed/**/*.js'],
  sassPattern: ['./seed/landing/static/landing/scss/**/*.scss', './seed/static/seed/scss/**/*.scss'],
  autoprefixerOptions: {
    browsers: ['last 3 versions', 'ie >= 8'],
    cascade: false
  },
  errorHandler: function (title) {
    return function (err) {
      $.util.log($.util.colors.red('[' + title + ']'), err.toString());
      if (this && this.hasOwnProperty('emit')) this.emit('end');
    };
  }
};

var eslint = function (fix) {
  fix = !!fix;
  return gulp.src(conf.jsPattern)
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

// Compile SCSS
gulp.task('sass', function () {
  return gulp.src(conf.sassPattern)
    .pipe($.sourcemaps.init())
    .pipe($.sass({noCache: true})).on('error', conf.errorHandler('Sass'))
    .pipe($.autoprefixer(conf.autoprefixerOptions)).on('error', conf.errorHandler('Autoprefixer'))
    .pipe($.csso())
    .pipe($.sourcemaps.write('.'))
    .pipe(gulp.dest('./seed/static/seed/css'));
});

// Monitor SCSS files and recompile on change
gulp.task('watch', ['sass'], function () {
  gulp.watch(conf.sassPattern, ['sass']);
});

// Default task
gulp.task('default', ['watch']);
