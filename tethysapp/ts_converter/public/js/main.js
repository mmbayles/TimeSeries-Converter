window.onbeforeunload = function() {
    $.ajax({
        url: 'delete-file'
    });
};
$(document).ready(function(){

    error_bool = $('#error_bool').text();
    error_message = $('#error_message').text()
    if (error_bool == 'True')
    {
        $('#modal').modal("show");
        alert(error_message);
    }
});