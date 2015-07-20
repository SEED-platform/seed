var gulp = require('gulp');
var concat = require('gulp-concat');
var sourcemaps = require('gulp-sourcemaps');
var uglify = require('gulp-uglify');
var ngAnnotate = require('gulp-ng-annotate'); //This makese angular syntax minification-friendly 
var less = require('gulp-less');
var jshint = require('gulp-jshint');
var path = require('path');

/* 	Concatenate all node js files into on js file for inclusion in page.
   	This task makes sure to concat the module declarations first so other Angular code doesn't get confused.
   	Uglify it along the way to reduce size.
 */

gulp.task('js',function(){
	gulp.src([	'seed/static/seed/js/seed.js', 
				'seed/static/seed/js/controllers/*.js', 
				'seed/static/seed/js/directives/*.js', 
				'seed/static/seed/js/filters/*.js', 
				'seed/static/seed/js/services/*.js'])
		.pipe(jshint({laxcomma:true}))
		.pipe(jshint.reporter('default')) //.pipe(concat('app.js'))
		.pipe(concat('app.js'))
		.pipe(ngAnnotate()) //.pipe(uglify()) //.pipe(sourcemaps.write())
		.pipe(gulp.dest('seed/static/seed/js'))
});


/* 	Compile .less to .css 
	Note we can minify and add source maps to this at some point, just like js.
*/
gulp.task('less:main', function(){
	return gulp.src('seed/static/seed/less/style.less')
			.pipe(less())
			.pipe(gulp.dest('seed/static/seed/css'));

});


gulp.task('less:landing', function(){
	return gulp.src('landing/static/landing/less/landing.less')
			.pipe(less())
			.pipe(gulp.dest('landing/static/landing/css'));
});


/*
gulp.task('test', function(){
	gulp.src(['seed/static/seed/tests/*.js'])
	.pipe(jshint({laxcomma:true}))
	.pipe(jshint.reporter('default')) 
	.pipe(concat('all_tests.js'))
	.pipe(gulp.dest('seed/static/seed/tests/'));

})
*/


/* 	Watch tasks ...  */

gulp.task('watch:js', function(){
	gulp.watch(['seed/static/seed/js/**/*.js', '!seed/static/seed/js/app.js'], ['js']);
})


//gulp.task('watch:test', function(){
//	gulp.watch(['seed/static/seed/tests/**/*.js', '!seed/static/seed/tests/all_tests.js'], ['test']);
//}) 


gulp.task('watch:css', function(){
	gulp.watch('seed/static/seed/less/**/*.less', ['less:main']);
	gulp.watch('landing/static/landing/less/**/*.less', ['less:landing']);
})


gulp.task('dev', ['js', 'watch:js', 'less:main', 'less:landing', 'watch:css' ])




