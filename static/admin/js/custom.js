(function($){ 
    $(document).ready(function(){
        $('#open_dialog').click(function(e){
            // e.preventDefault();
            $("#iframe_dialog").dialog({
                title: "Copy Iframe Code",
                dialogClass: "no-close",
                resizable: false,
                buttons: [
                    {
                        text: "Copy",
                        icon: "ui-icon-copy",
                        click: function() {
                            $("textarea.iframe_code").select();
                            document.execCommand('copy');
                        }
                    },
                    {
                        text: "Close",
                        icon: "ui-icon-closethick",
                        click: function() {
                            $( this ).dialog( "close" );
                        }
                    }
                ],
                height: 200,
                modal: true,
                width: 700,
                draggable: false,
                show: { 
                    effect: "fade",
                    duration: 300
                }
            }); 
        });
    });
})(django.jQuery);