window.onbeforeunload = function() {
    $.ajax({
        url: 'delete-file',

        error: function(error, text, thing) {
            console.log(error);
            console.log(text);
            console.log(thing);
        }
    });
};