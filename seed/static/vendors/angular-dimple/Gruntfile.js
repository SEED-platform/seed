// ┌─────────────┐
// │ Gruntfile   │
// └─────────────┘
// Grunt wraps several tasks to ease development
// runs acetate, deploys the site, and tags new releases
var fs = require('fs');

// Gets current version description from CHANGELOG.md
function findVersion(log) {
  var newVersion = log.split('## v')[1];
  var description = newVersion.substring(5,newVersion.length);
  return description;
}

module.exports = function(grunt) {
  var pkg = grunt.file.readJSON('package.json');
  var name = pkg.name;
  var repo = pkg.repository.split('github.com/')[1];
  var currentVersion = 'v' + pkg.version;
  var log = grunt.file.read('CHANGELOG.md');
  var description = findVersion(log);

  // Javascript banner
  var banner = '/*! ' + name + ' - <%= pkg.version %> - <%= grunt.template.today("yyyy-mm-dd") %>\n' +
               '*   https://github.com/' + repo + '\n' +
               '*   Licensed ISC */\n';

  //require('load-grunt-tasks')(grunt);
  grunt.loadNpmTasks('grunt-contrib-concat');
  grunt.loadNpmTasks('grunt-contrib-watch');
  grunt.loadNpmTasks('grunt-contrib-jshint');

  grunt.initConfig({
    pkg: grunt.file.readJSON('package.json'),

    // Build documentation site
    'acetate': {
      build: {
        config: 'acetate.conf.js'
      },
      watch: {
        config: 'acetate.conf.js',
        options: {
          watch: true,
          server: true
        }
      }
    },

    // Watch sass, images, and javascript
    'watch': {
      sass: {
        files: ['docs/source/assets/css/**/*'],
        tasks: ['sass']
      },
      img: {
        files: ['docs/source/assets/img/**/*'],
        tasks: ['newer:imagemin']
      },
      js: {
        files: ['docs/source/assets/js/**/*', 'lib/**.*'],
        tasks: ['lib', 'jshint:docs', 'copy:docs']
      }
    },

    // Build site sass
    'sass': {
      expanded: {
        options: {
          style: 'expanded',
          sourcemap: 'none',
          loadPath: 'bower_components'
        },
        files: {
          'docs/build/assets/css/style.css': 'docs/source/assets/css/style.scss'
        }
      }
    },

    // Optimize images
    'imagemin': {
      doc: {
        files: [{
          expand: true,
          cwd: 'docs/source/assets/img',
          src: ['**/*.{png,jpg,svg}'],
          dest: 'docs/build/assets/img/'
        }]
      }
    },

    // Check js for errors
    'jshint': {
      lib: [
        'lib/**/*.js'
      ],
      docs: [
        'docs/source/assets/js/**.js'
      ]
    },

    // Concatenate lib
    'concat': {
      options: {
        stripBanners: true,
        banner: banner
      },
      dist: {
        src: ['lib/*.js'],
        dest: 'dist/' + name + '.js'
      }
    },

    // Minified version of lib
    'uglify': {
      dist: {
        src: ['lib/*.js'],
        dest: 'dist/' + name + '.min.js'
      }
    },

    // Copy files
    'copy': {
      dist: {
        expand: true,
        cwd: 'dist/',
        src: ['*'],
        dest: 'docs/source/assets/js/lib/'
      },
      docs: {
        expand: true,
        cwd: 'docs/source/assets/js/',
        src: ['**/*'],
        dest: 'docs/build/assets/js/'
      },
      data: {
        expand: true,
        cwd: 'docs/source/data',
        src: ['*'],
        dest: 'docs/build/data/'
      }
    },

    // Make a zip file of the dist folder
    'compress': {
      main: {
        options: {
          archive: name + '.zip'
        },
        files: [
          {
            src: ['dist/**'],
            dest: './'
          },
        ]
      }
    },

    // This task runs right after npm install
    'concurrent': {
      prepublish: [
        'sass',
        'uglify',
        'copy',
        'concat:dist',
        'newer:imagemin'
      ]
    },

    // Release a new version on GitHub
    'github-release': {
      options: {
        repository: repo,
        release: {
          tag_name: currentVersion,
          name: currentVersion,
          body: description
        }
      },
      files: {
        src: name + '.zip'
      }
    },

    // Ask for GitHub username and password
    'prompt': {
      github: {
        options: {
          questions: [
            {
              config: 'github-release.options.auth.user',
              type: 'input',
              message: 'GitHub username:'
            },
            {
              config: 'github-release.options.auth.password',
              type: 'password',
              message: 'GitHub password:'
            }
          ]
        }
      }
    },

    // Deploy the docs site to gh-pages
    'gh-pages': {
      options: {
        base: 'build',
        repo: 'https://github.com/' + repo + '.git'
      },
      src: ['**']
    }
  });

  // Build a dist folder with all assets
  grunt.registerTask('prepublish', [
    'concurrent:prepublish'
  ]);

  grunt.registerTask('lib', ['jshint:lib', 'concat:dist', 'uglify:dist']);
  grunt.registerTask('deploy', ['lib', 'acetate:build', 'sass', 'newer:imagemin', 'gh-pages']);

    // Release a new version of the framework
  grunt.registerTask('release', [
    'prompt:github',
    'prepublish',
    'compress',
    'github-release'
  ]);

  grunt.registerTask('default', ['lib', 'jshint:docs', 'copy', 'newer:imagemin', 'sass', 'acetate:watch', 'watch']);

};
