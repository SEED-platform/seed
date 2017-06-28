
var tmp = require('tmp');
module.exports = function(grunt) {
    grunt.initConfig({
        // connect: {
        //     options: {
        //         port: 8000,
        //         hostname: 'localhost'
        //     },
            // runtime: {
            //     options: {
            //         middleware: function (connect) {
            //             return [
            //                 lrSnippet,
            //                 mountFolder(connect, 'protractorInstrumented'),
            //                 mountFolder(connect, '.......')
            //             ];
            //         }
            //     }
            // }

        // Before generating any new files, remove any previously-created files.
        // },
        clean: {
          options: {
            force:true
          },
          tests: ['tmp', 'build', 'protractorInstrumented', 'protractorCoverage', 'protractorReports', 'protractorSaved'],
        },
        connect: {
          server: {
            options: {
              port: 3000,
              base: 'protractorInstrumented/seed/static/seed/js'
            }
          },
        },
        instrument: {
            files: ['seed/static/seed/js/**/*.js','!seed/static/seed/js/decorators/**/*.js', '!seed/static/seed/js/seed.js'],
            options: {
            lazy: true,
                basePath: "protractorInstrumented"
            }
        },
        copy: {
          'save': {
            expand: true,
            cwd: 'seed/static/seed/js',
            src: '**',
            dest: 'protractorSaved/'
          },
          'instrument': {
            expand: true,
            cwd: 'protractorInstrumented/seed/static/seed/js',
            src: '**',
            dest: 'seed/static/seed/js/'
          },
          'copyBack': {
            expand: true,
            cwd: 'protractorSaved',
            src: '**',
            dest: 'seed/static/seed/js/'
          },
        },
        protractor_coverage: {
            options: {
                keepAlive: false, // If false, the grunt process stops when the test fails.
                noColor: false,
                coverageDir: 'protractorCoverage',
                args: {
                    baseUrl: 'http://localhost:8000'
                }
            },
            local: {
                options: {
                    configFile: 'seed/static/seed/tests/protractor-tests/protractorConfigCoverage.js'
                }
            }
        },
        makeReport: {
            src: 'protractorCoverage/**/*.json',
            options: {
                type: 'lcov',
                dir: 'protractorReports',
                print: ''
            }
        },
        coveralls: {
            main:{
                src: 'protractorReports/**/*.info',
                options: {
                    force: true
                },
            },
        },
    });

    // Actually load this plugin's task(s).
    // grunt.loadTasks('tasks');

    // These plugins provide necessary tasks.
    grunt.loadNpmTasks('grunt-protractor-coverage');
    grunt.loadNpmTasks('grunt-contrib-clean');
    grunt.loadNpmTasks('grunt-contrib-copy');
    grunt.loadNpmTasks('grunt-istanbul');
    grunt.loadNpmTasks('grunt-coveralls');

    // Whenever the "test" task is run, first clean the "tmp" dir, then run this
    // plugin's task(s), then test the result.

    //same as npm test more or less
    // grunt.registerTask('coverage', ['protractor_coverage:local']);
    
    //don't use instrumented code
    // grunt.registerTask('coverage', ['clean', 'copy:save', 'instrument', 'protractor_coverage:local', 'copy:copyBack']);    

    //without coveralls
    grunt.registerTask('coverage', ['clean', 'copy:save', 'instrument', 'copy:instrument', 'protractor_coverage:local', 'copy:copyBack', 'makeReport']);
    grunt.registerTask('report', ['makeReport']);

    //with coveralls
    // grunt.registerTask('coverage', ['clean', 'copy:save', 'instrument', 'copy:instrument', 'protractor_coverage:local', 'copy:copyBack', 'makeReport', 'coveralls']);

    grunt.registerTask('test', ['coverage']);
};
