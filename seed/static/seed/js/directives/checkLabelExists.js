angular.module('checkLabelExists', []).directive('checkLabelExists', function() {
  return {
    require: 'ngModel',
    scope: {
      existingLabels: "=checkLabelExists"
    },
    link: function(scope, elm, attrs, ctrl) {

      ctrl.$validators.checkLabelExists = function(modelValue) {

        if(!modelValue) return true;

        var labels = scope.existingLabels;
        if (!labels) return true;

        var len=labels.length;
        for (var index=0; index<len; index++){
          var label=labels[index];
          if (label.name===modelValue){
            return false;
          }
        }

        return true;
        
      };
    }
  };
});