function $new(tagName, attrs) {
  return jQuery(document.createElement(tagName)).attr(attrs || {});
}

var Turkanet = {};

Turkanet.LabelingUI = function (form) {
  var start = new Date();

  var submitted = false;

  var input = form.find('input[type=text]');

  form.find('input[type=button]').click(function () {
    var value = jQuery.trim(input.val());

    if (value.length > 0) {
      input.addClass('block');

      input = $new('input', {'type': 'text', 'name': 'label'}).insertAfter(input);
    }
  });

  form.submit(function () {
    if (submitted) {
      return false;
    } else {
      submitted = true;

      form.find(':submit').attr('disabled', true);

      form.find('input[name=time]').val(new Date() - start);
    }
  });
}