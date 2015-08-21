module.exports = function (acetate) {
  acetate.global('config', {
    environment: 'dev'
  });

  acetate.layout('**/*', 'layouts/_layout:content');
  acetate.layout('posts/**/*', 'layouts/_post:post');

  acetate.options.src = 'docs/source';
  acetate.options.dest = 'docs/build';
};