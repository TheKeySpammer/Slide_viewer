(function($){ 
    $(document).ready(function(){
        $('.generate_model').click(function(e){
            e.preventDefault();
            var _this = $(this);
            $.ajax({
                type: "POST",
                data: {'user_id': 1},
                dataType: 'JSON',
                url: "/testapp/testapp/search_location/",
                beforeSend: function(xhr, settings) {
                    function getCookie(name) {
                        var cookieValue = null;
                        if (document.cookie && document.cookie !== '') {
                            var cookies = document.cookie.split(';');
                            for (var i = 0; i < cookies.length; i++) {
                                var cookie = cookies[i].trim();
                                // Does this cookie string begin with the name we want?
                                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                                    break;
                                }
                            }
                        }
                        return cookieValue;
                    }
                    xhr.setRequestHeader("X-CSRFToken", getCookie('csrftoken'));
                    // image.hide();
                    // loading.show();
                },
                // statusCode: {
                //     200: function() {
                //         loading.hide();
                //         image.attr('src', '/static/img/success.png');
                //         image.show();
                //     },
                //     404: function() {
                //         loading.hide();
                //         image.attr('src', '/static/img/error.png');
                //         image.show();
                //     },
                //     500: function() {
                //         loading.hide();
                //         image.attr('src', '/static/img/error.png');
                //         image.show();
                //     }
                // }
            });
        });
    });
})(django.jQuery);