
$(document).ready(function () {

    // Get application name
    var current_path_array = window.location.pathname.split('/');
    var appname = current_path_array[1];

    paper.install(window);

    // Variable declarations
    var ppm = 1000000;
    var viewer_is_new;
    var bm_center;
    var bm_zoom;
    var bm_goto;
    var rotator; // Stores the Rotation slider data
    var annotation_border_picker; // Stores the Overlay Border color data
    var default_border_color = "Red";
    var editMode = false;
    var currentEditingOverlay = null;
    var paperOverlay;
    var viewerOpen = false;
    var stroke_color = default_border_color;
    var stroke_width = 4;
    var selectingColor = false;
    var viewZoom;
    var rotating = false;
    var showingAnnotation = true;
    var hitTest = null;
    var isFullScreen = false;
    var csrftoken = getCookie('csrftoken');
    var currentFocus = 0;
    var syncLock = false;
    var prevZoom = 0;
    var prevPan = new OpenSeadragon.Point();
    var annoationLinesScaling = true;
    var slideTrayPercent = 0.25;
    var slideTrayLargeSize = 290;
    var slideTrayMedSize = 150;
    var slideTraySmallSize = 80;

    // Tooltip Variable Settings
    OpenSeadragon.setString('Tooltips.SelectionToggle', 'Selection Demo');
    OpenSeadragon.setString('Tooltips.SelectionConfirm', 'Ok');
    OpenSeadragon.setString('Tooltips.SelectionCancel', 'Cancel');
    OpenSeadragon.setString('Tooltips.ImageTools', 'Image tools');
    OpenSeadragon.setString('Tool.brightness', 'Brightness');
    OpenSeadragon.setString('Tool.contrast', 'Contrast');
    OpenSeadragon.setString('Tool.reset', 'Reset');
    OpenSeadragon.setString('Tooltips.HorizontalGuide', 'Add Horizontal Guide');
    OpenSeadragon.setString('Tooltips.VerticalGuide', 'Add Vertical Guide');
    OpenSeadragon.setString('Tool.rotate', 'Rotate');
    OpenSeadragon.setString('Tool.close', 'Close');


    var currentUrl = new URL(window.location.href);
    var urlConfig = currentUrl.searchParams.get('config');

    var config = null;
    if (urlConfig !== null) {
        try {
            config = JSON.parse(urlConfig);
        } catch (err) {
            config = null;
        }
    }


    var openSlides = [];
    var viewers = [];
    if (config !== null) {
        var cSlides = config.slides;
        for (let index = 0; index < cSlides.length; index++) {
            const slide = cSlides[index];
            var slotId = 'slot-' + (index + 1);
            openSlides.push({
                'id': slide.id,
                'slot': slotId,
                'image': '/' + appname + '/' + slide.id + '.dzi'
            });
            var v = createViewer('/' + appname + '/' + slide.id + '.dzi', slide.rotation);
            viewers.push(v);
            if (index > 0) {
                $('#' + slotId).removeClass('text-light');
                $('#' + slotId).addClass('is-selected');
                $('#' + slotId).off('click');
                $('#' + slotId).html(slide.name);
            }
        }

        setTimeout(function () {
            for (let index = 0; index < viewers.length; index++) {
                const v = viewers[index];
                const slide = cSlides[index];
                if (index == 0) {
                    $("#rotation-selector").data("roundSlider").setValue(slide.rotation);
                }
                $("#openseadragon-rotator-" + (index + 1)).data('roundSlider').setValue(slide.rotation);
                var viewport = v.viewport;
                viewport.setRotation(slide.rotation);
                viewport.panTo(new OpenSeadragon.Point(slide.center.x, slide.center.y));
                viewport.zoomTo(slide.zoom);
            }
        }, 800);

    } else {
        openSlides.push({
            'id': parseInt(slideId),
            'slot': 'slot-1',
            'image': image
        });
        viewers.push(createViewer(image));
    }

    var viewer = viewers[0];


    function csrfSafeMethod(method) {
        // these HTTP methods do not require CSRF protection
        return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
    }
    $.ajaxSetup({
        beforeSend: function (xhr, settings) {
            if (!csrfSafeMethod(settings.type) && !this.crossDomain) {
                xhr.setRequestHeader("X-CSRFToken", csrftoken);
            }
        }
    });


    /*
    0 - Drawing Mode off
    1 - Line Mode
    2 - Rect Mode
    3 - Circle Mode
    */
    var drawMode = 0;
    var startPoint = null;
    var currentLine = null;
    var lines = [];

    var lineDB = [];

    var currentRect = null;
    var rects = [];

    var currentCircle = null;
    var circles = [];
    var lastOverlay;

    // Prevent Caman from caching the canvas because without this:
    // 1. We have a memory leak
    // 2. Non-caman filters in between 2 camans filters get ignored.
    var caman = Caman;
    caman.Store.put = function() {};

    $(".navbar").mouseover(function () {
        currentFocus = 0;
        prevZoom = viewer.viewport.getZoom();
        prevPan = viewer.viewport.getCenter();
    });

    // Viewer Event handlers

    viewer.addHandler("open", function () {
        viewer.source.minLevel = 8;
        /* Start zoomed in, then return to home position after
        loading.  Workaround for blurry viewport on initial
        load (OpenSeadragon #95). */
        var center = new OpenSeadragon.Point(0.5,
            1 / (2 * viewer.source.aspectRatio));
        viewer.viewport.zoomTo(2, center, true);
        viewer_is_new = true;

        setTimeout(function () {
            $("#home-btn").css({
                'background-color': '#3298dc',
                'color': 'white'
            });

            viewer.viewport.minZoomLevel = viewer.viewport.getHomeZoom();
            viewerOpen = true;
            stroke_width = stroke_width / paper.view.zoom;
            viewZoom = paper.view.zoom;
            loadAnnotations();
        }, 500);

        viewer.drawer.viewer = viewer;
    });

    viewer.addHandler("update-viewport", function () {
        if (viewer_is_new) {
            setTimeout(function () {
                if (viewer.viewport) {
                    viewer.viewport.goHome(false);
                }
            }, 5);
            viewer_is_new = false;
        }
        lines.forEach(function (line) {
            updateLineCardDivText(line.text, line.line.firstSegment.point, line.line.lastSegment.point);
        });
        rects.forEach(function (rect) {
            updateRectCardDivText(rect.text, rect.rect.strokeBounds.topLeft, rect.rect.strokeBounds.topRight, rect.rect.strokeBounds.bottomRight);
        });
        circles.forEach(function (circle) {
            updateCircleCardDivText(circle.text, circle.circle.position.add(new Point(0, circle.circle.radius + circle.circle.strokeWidth)), circle.circle.radius);
        });

    });

    viewer.addHandler("home", function () {
        if (bm_goto) {
            setTimeout(function () {
                if (viewer.viewport) {
                    viewer.viewport.zoomTo(bm_zoom, bm_center, false);
                }
            }, 200);
            bm_goto = false;
        }
        rotator.setValue(0);
        updateRotation(0);
        resetZoomButtons();
        fixRotatorTooltip();
    });


    viewer.addHandler("zoom", function (event) {
        $("#zoom-value-display").html("");
        zoom_level = viewer.viewport.getZoom();
        if (zoom_level >= 1) {
            $("#zoom-value-display").html(Math.round(zoom_level) + "x");
        } else {
            $("#zoom-value-display").html(zoom_level.toFixed(2).toString().substring(1) + "x");
        }

        if (!viewerOpen) return;
        var z = event.zoom;
        var homeZoom = viewer.viewport.getHomeZoom();
        if (z.toFixed(2) == homeZoom.toFixed(2) && viewer.viewport.getRotation() == 0) {
            $("#home-btn").css({
                'background-color': '#3298dc',
                'color': 'white'
            });
            $("#btn-rotate-preset-1").removeClass("is-info");
        } else {
            $("#home-btn").css({
                'background-color': 'rgba(0, 0, 0, 0)',
                'color': '#363636'
            });
        }

        // ANNOTATION LINES SCALING CODE 

        if (prevZoom != 0 && annoationLinesScaling) {
            var delta = viewer.viewport.getZoom() / prevZoom;
            for (var i = 0; i < lines.length; i++) {
                lines[i].line.strokeWidth = lines[i].line.strokeWidth / delta;
            }
            for (var i = 0; i < circles.length; i++) {
                circles[i].circle.strokeWidth = circles[i].circle.strokeWidth / delta;
            }

            for (var i = 0; i < rects.length; i++) {
                rects[i].rect.strokeWidth = rects[i].rect.strokeWidth / delta;
            }

        }


        if (currentFocus == 0 && syncLock) {
            var currZoom = viewer.viewport.getZoom();
            var delta = currZoom / prevZoom;

            for (let index = 1; index < viewers.length; index++) {
                const element = viewers[index];
                element.viewport.zoomTo(element.viewport.getZoom() * delta);

            }
        }

        if (currentFocus == 0) {
            prevZoom = viewer.viewport.getZoom();
        }


        $(".zoom-button").get().forEach(function (btn) {
            switch (parseInt(btn.value)) {
                case 2:
                    if (z == 2) {
                        $(btn).addClass("orange-button");
                    } else {
                        $(btn).removeClass("orange-button");
                    }
                    break;

                case 5:
                    if (z == 5) {
                        $(btn).addClass("red-button");
                    } else {
                        $(btn).removeClass("red-button");
                    }
                    break;

                case 10:
                    if (z == 10) {
                        $(btn).addClass("yellow-button");
                    } else {
                        $(btn).removeClass("yellow-button");
                    }
                    break;

                case 20:
                    if (z == 20) {
                        $(btn).addClass("green-button");
                    } else {
                        $(btn).removeClass("green-button");
                    }
                    break;

                case 40:
                    if (z == 40) {
                        $(btn).addClass("blue-button");
                    } else {
                        $(btn).removeClass("blue-button");
                    }
                    break;
            }
        });

    });

    viewer.addHandler("rotate", function (event) {
        if (!viewerOpen) return;
        $("#btn-rotate-preset-1").removeClass("is-info");
        $("#btn-rotate-preset-2").removeClass("is-info");
        $("#btn-rotate-preset-3").removeClass("is-info");

        switch (event.degrees) {
            case 0:
                $("#btn-rotate-preset-1").addClass("is-info");
                break;
            case 90:
                $("#btn-rotate-preset-2").addClass("is-info");
                break;
            case 180:
                $("#btn-rotate-preset-3").addClass("is-info");
                break;
        }


        // var rot = viewer.viewport.getRotation();
        // for (let index = 1; index < viewers.length; index++) {
        //     const element = viewers[index];
        //     element.viewport.setRotation(rot);
        // }

        var homeZoom = viewer.viewport.getHomeZoom();
        if (viewer.viewport.getZoom().toFixed(2) == homeZoom.toFixed(2) && event.degrees == 0) {
            $("#home-btn").css({
                'background-color': '#3298dc',
                'color': 'white'
            });
            $("#btn-rotate-preset-1").removeClass("is-info");
        } else {
            $("#home-btn").css({
                'background-color': 'rgba(0, 0, 0, 0)',
                'color': '#363636'
            });
        }
    });


    viewer.addHandler('pan', function () {

        if (currentFocus == 0 && syncLock) {
            var center = viewer.viewport.getCenter();
            var delta = center.minus(prevPan);
            var dPix = viewer.viewport.deltaPixelsFromPoints(delta);
            for (let index = 1; index < viewers.length; index++) {
                const element = viewers[index];
                element.viewport.panBy(element.viewport.deltaPointsFromPixels(dPix));
            }
        }

        if (currentFocus == 0) {
            prevPan = viewer.viewport.getCenter();
        }
    });


    
    // Openseadragon Plugin initialization
    bulmaSlider.attach();
    $("#brightness-slider").on('change', function(e) {
        updateFilters();
    });
    
    $("#red-slider").on('change', function(e) {
        updateFilters();
    });
    
    $("#green-slider").on('change', function(e) {
        updateFilters();
    });
    
    $("#blue-slider").on('change', function(e) {
        updateFilters();
    });
    
    $(".undo-button-brightness").click(function() {
        $("#brightness-slider").val(0);
        updateFilters();
    })

    function updateFilters() {
        var brightness = $("#brightness-slider").val();
        brightness = parseInt(brightness);
        var red = $("#red-slider").val();
        var green = $("#green-slider").val();
        var blue = $("#blue-slider").val();
        var strength = 50;
        red = parseInt(red);
        green = parseInt(green);
        blue = parseInt(blue);
        viewer.setFilterOptions({
            filters: {
                processors: [OpenSeadragon.Filters.BRIGHTNESS(brightness),
                    function(context, callback) {
                        caman(context.canvas, function() {
                            this.colorize(red, green, blue, strength);
                            this.render(callback);
                        });
                    }]
            },
            loadMode: 'sync'
        });

    }

    // Scalebar plugin

    viewer.scalebar({
        type: OpenSeadragon.ScalebarType.MICROSCOPY,
        pixelsPerMeter: ppm,
        minWidth: "160px",
        location: OpenSeadragon.ScalebarLocation.BOTTOM_LEFT,
        yOffset: 40,
        stayInsideImage: false,
        color: "blue",
        fontColor: "blue",
        backgroundColor: "rgb(255, 255, 255, 0.8)",
        fontSize: "large",
        barThickness: 4
    });



    // Paperjs overlay
    paperOverlay = viewer.paperjsOverlay();

    // Other tool Initialization

    // Rotation slider
    $("#rotation-selector").roundSlider({
        radius: 45,
        width: 8,
        handleSize: "+8",
        handleShape: "dot",
        sliderType: "min-range",
        value: 50,
        tooltipFormat: tooltipInDegrees,
        change: updateRotationSlider,
        drag: updateRotationSlider,
        min: 0,
        max: 360,
        start: function () {
            rotating = true;
        },
        stop: function () {
            rotating = false;
            if (!$("#rotation-selector-dropdown").is(":hover")) {
                $("#rotation-selector-dropdown").removeClass("is-active");
                $("#rotation-dropdown-button").css({
                    'background-color': 'rgba(0, 0, 0, 0)',
                    'color': '#363636'
                });
            }
        }
    });

    // Event Handlers for Rotation Slider
    function tooltipInDegrees(args) {
        return args.value + "°";
    }

    function updateRotationSlider(e) {
        updateRotation(e.value);
    }

    rotator = $("#rotation-selector").data("roundSlider");

    // Fix tooltip not in center
    setTimeout(function () {
        fixRotatorTooltip();
    }, 500);

    function fixRotatorTooltip() {
        $(".rs-tooltip").css({
            "margin-top": "-15.5px",
            "margin-left": "-16.652px"
        });
    }

    // Color picker initialization
    // Overlay Border
    // annotation_border_picker = Pickr.create({
    //     el: '#annotation-border-picker',
    //     theme: 'nano', // or 'monolith', or 'nano'
    //     default: default_border_color,

    //     swatches: [
    //         'red',
    //         'yellow',
    //         'green',
    //         'black',
    //         'orange',
    //         'purple',
    //         'gray'
    //     ],

    //     components: {

    //         // Main components
    //         preview: true,
    //         opacity: false,
    //         hue: true,

    //         // Input / output Options
    //         interaction: {
    //             hex: false,
    //             rgba: false,
    //             hsla: false,
    //             hsva: false,
    //             cmyk: false,
    //             input: false,
    //             clear: true,
    //             save: true
    //         }
    //     }
    // });

    // Overlay Background

    // annotation_border_picker.on('save', function (event) {
    //     annotation_border_picker.hide();
    //     stroke_color = annotation_border_picker.getColor().toHEXA().toString();
    // });


    // annotation_border_picker.on('change', function (event) {
    //     stroke_color = annotation_border_picker.getColor().toHEXA().toString();
    // });

    // annotation_border_picker.on('show', function (event) {
    //     selectingColor = true;
    // });

    // annotation_border_picker.on('hide', function (event) {
    //     selectingColor = false;
    // });


    $(".color-palette").click(function (event) {
        stroke_color = event.target.title;
        $("#annotation-border-picker").css({
            'background-color': stroke_color
        });
    });

    $("#stroke-width-input").on('change', function (event) {
        stroke_width = event.target.valueAsNumber;
        stroke_width = stroke_width / 2;
        stroke_width = stroke_width / viewZoom;
    });


    $("#annotation-hide-button").click(function () {
        var i;
        if (showingAnnotation) {
            $(this).attr('title', 'Show Annotation');
            $(this).children("svg").remove();
            i = document.createElement("i");
            $(i).addClass("far");
            $(i).addClass("fa-eye-slash");
            $(this).append(i);
            lines.forEach(function (line) {
                line.line.visible = false;
                $(line.text).hide();
            });

            rects.forEach(function (rect) {
                rect.rect.visible = false;
                $(rect.text).hide();
            });

            circles.forEach(function (circle) {
                circle.circle.visible = false;
                $(circle.text).hide();
            });


        } else {
            $(this).attr('title', 'Hide Annotation');
            $(this).children("svg").remove();
            i = document.createElement("i");
            $(i).addClass("far");
            $(i).addClass("fa-eye");
            $(this).append(i);

            lines.forEach(function (line) {
                line.line.visible = true;
                $(line.text).show();
            });

            rects.forEach(function (rect) {
                rect.rect.visible = true;
                $(rect.text).show();
            });

            circles.forEach(function (circle) {
                circle.circle.visible = true;
                $(circle.text).show();
            });


        }
        showingAnnotation = !showingAnnotation;
    });

    $("#navigator-hide-button").click(function () {
        $('.openseadragon-container div:nth-child(2)').toggle();
        $(this).toggleClass('navigator-hide-class');
    });

    $("#stats-button").click(function () {
        $("#stats-modal").addClass("is-active");
    });

    $(".stats-modal-close").click(function () {
        $("#stats-modal").removeClass("is-active");
    });

    $("#sync-lock-button").click(function () {
        var i;
        if (syncLock) {
            $(this).attr('title', 'Lock Sync');
            $(this).children("svg").remove();
            i = document.createElement("i");
            $(i).addClass("fas");
            $(i).addClass("fa-lock-open");
            $(this).append(i);
            if (viewers.length > 1) {
                $('.rotation-selector-class').show();
            }
            for (let index = 1; index < openSlides.length; index++) {
                $("#slot-delete-" + (index + 1)).show();
            }

            $(".text-light").on('click', addSlideEvent);
        } else {
            $(this).attr('title', 'Unclok Sync');
            $(this).children("svg").remove();
            i = document.createElement("i");
            $(i).addClass("fas");
            $(i).addClass("fa-lock");
            $(this).append(i);
            if (viewers.length > 1) {
                $('.rotation-selector-class').hide();
            }
            $(".text-light").off('click');

            for (let index = 1; index < openSlides.length; index++) {
                $("#slot-delete-" + (index + 1)).hide();
            }
        }
        syncLock = !syncLock;
    });


    function createViewer(image) {
        var label_container_template = `
        <div class="label-container">

            <div class="label-img-container">
                <div class="card">
                    <header class="card-header">
                        <p class="card-header-title">
                            <i class="card-header-icon label-rotate-btn" >
                                <span class="icon">
                                    <i class="fas fa-sync" aria-hidden="true"></i>
                                </span>
                            </i>
                        </p>
                        <i class="card-header-icon label-close-btn" aria-label="close label">
                            <span class="icon">
                                <i class="fas fa-times" aria-hidden="true"></i>
                            </span>
                        </i>

                    </header>
                    <div class="card-content">
                        <div class="content label_img_content_container">
                            
                        </div>
                    </div>

                </div>
            </div>
        </div>
        `;

        var label_button_template = `
        <div class="label_button">
            <button>
                <i class="fas fa-info"></i>
            </button>
        </div>
        `;

        var id = viewers.length + 1;
        if (id > 4) {
            return null;
        }
        var navbarHeight = $(".navbar").height();
        var pageHeight = $("#page").height();


        $("#slide-tray-container").css({
            'height': slideTrayLargeSize + 'px'
        });

        var element = document.createElement('div');
        $(element).attr('id', 'openseadragon-viewer-' + id);
        $(element).addClass('viewer');
        $("#viewer-container").append(element);
        if (id == 2) {
            $("#zoom-value-container").hide();
        }

        switch (id) {
            case 1:
                $(element).css({
                    width: '100%',
                    height: (pageHeight) + 'px',
                    position: 'absolute',
                    left: 0,
                    top: 0
                });

                break;

            case 2:
                $("#openseadragon-viewer-1").css({
                    width: '50%'
                });
                $(element).css({
                    width: '50%',
                    height: (pageHeight) + 'px',
                    position: 'absolute',
                    right: '0',
                    top: '0'
                });

                $('#openseadragon-rotator-1').css({
                    left: $("#openseadragon-viewer-1").position().left + $("#openseadragon-viewer-1").width() - 100,
                });
                break;

            case 3:
                $("#openseadragon-viewer-2").css({
                    width: '50%',
                    height: ((pageHeight) / 2) + 'px',
                    right: 0,
                    top: 0,
                });

                $(element).css({
                    width: '50%',
                    height: ((pageHeight) / 2) + 'px',
                    position: 'absolute',
                    right: '0',
                    bottom: '0'
                });


                break;
            case 4:
                $(element).css({
                    width: '50%',
                    height: ((pageHeight) / 2) + 'px',
                    position: 'absolute',
                    left: '0',
                    bottom: '0'
                });
                $("#openseadragon-viewer-1").css({
                    width: '50%',
                    height: ((pageHeight) / 2) + 'px',
                    left: 0,
                    top: 0,
                });
                break;
        }

        var v = OpenSeadragon({
            id: "openseadragon-viewer-" + id,
            prefixUrl: "/static/images/",
            showNavigator: true,
            animationTime: 0.5,
            blendTime: 0.1,
            constrainDuringPan: false,
            maxZoomPixelRatio: 2,
            minPixelRatio: 0.5,
            //   minZoomLevel: 0.653,
            visibilityRatio: 1,
            zoomPerScroll: 2,
            crossOriginPolicy: "Anonymous",
            navigatorPosition: 'TOP_LEFT',
            zoomInButton: "zoomin-btn",
            zoomOutButton: "zoomout-btn",
            homeButton: "home-btn",
            navigatorBackground: '#fff',
        });
        $("#openseadragon-viewer-" + id + " .navigator").css({
            'background-color': 'rgb(255, 255, 255)',
            'border': '1px solid rgb(255, 255, 255)',
            'box-shadow': '0px 3px 15px rgba(150, 150, 150, 0.9)',
        });



        var rotationToolContainer = document.createElement('div');
        $(rotationToolContainer).addClass('rotation-selector-class');
        $(rotationToolContainer).attr('id', 'openseadragon-rotator-' + id);
        $(rotationToolContainer).css({
            position: 'absolute',
            top: $("#openseadragon-viewer-" + id).position().top,
            left: $("#openseadragon-viewer-" + id).position().left + $("#openseadragon-viewer-" + id).width() - 100,
        });

        switch (id) {
            case 1:
                $("#openseadragon-viewer-1 div:nth-child(2)").css({
                    'margin-top': '90px'
                });
                $(rotationToolContainer).css({
                    'margin-top': '90px'
                });
                break;
            case 2:
                $("#openseadragon-viewer-2 div:nth-child(2)").css({
                    'margin-top': '90px'
                });
                $(rotationToolContainer).css({
                    'margin-top': '90px'
                });
                break;
            case 3:
                break;
            case 4:
                break;
        }

        $(rotationToolContainer).roundSlider({
            radius: 45,
            width: 8,
            handleSize: "+8",
            handleShape: "dot",
            sliderType: "min-range",
            tooltipFormat: tooltipInDegrees,
            change: function (e) {
                v.viewport.setRotation(e.value);
                if (id == 1) {
                    if (rotator != undefined) {
                        rotator.setValue(e.value);
                    }
                }
            },
            drag: function (e) {
                v.viewport.setRotation(e.value);
            },
            value: 0,
            min: 0,
            max: 360,
        });


        if (id == 1) {
            $(rotationToolContainer).hide();
        } else if (id > 1) {
            $("#openseadragon-rotator-1").show();
        }


        $("#page").append(rotationToolContainer);

        // Add image info button
        var label_button = $(label_button_template).clone();
        var label_container = $(label_container_template).clone();
        var rotator_height = 0;
        if (id != 1) {
            rotator_height = $(rotationToolContainer).height()
        }
        label_button.css({
            position: 'absolute',
            top: $("#openseadragon-viewer-" + id).position().top + rotator_height + 5,
            left: $("#openseadragon-viewer-" + id).position().left + $("#openseadragon-viewer-" + id).width() - 80,
        });
        label_button.attr('id', 'label_button_' + id);

        label_container.attr('id', 'label_container_' + id);


        $(label_button).find("button").click(function () {
            $(label_button).hide();
            label_container.show();
        });

        $(label_container).find(".label-close-btn").click(function () {
            $(label_container).hide();
            $(label_button).show();
        });
        label_container.hide();
        label_button.hide();


        var image_id = image.split('/')[2].split('.')[0];

        var img = new Image();

        img.onload = function () {
            var height = this.height;
            var width = this.width;

            if (height > 450) {
                var ratio = width / height;
                height = 450;
                width = ratio * height;
                $(this).height(height);
                $(this).width(width);
            }
            if (width > 200) {
                var ratio = height / width;
                width = 200;
                height = ratio * width;
                $(this).height(height);
                $(this).width(width);
            }
            this.id = "label_img_img-" + id;
            label_container.css({
                position: 'absolute',
                top: $("#openseadragon-viewer-" + id).position().top + rotator_height + 5,
                left: $("#openseadragon-viewer-" + id).position().left + $("#openseadragon-viewer-" + id).width() - 30 - width,
            });
            label_container.show();

        };
        img.src = '../' + image_id + '/label';
        label_container.find('.label_img_content_container').append(img);


        label_container.find('.label-rotate-btn').click(function () {
            var label = $(label_container).find('img');
            if (label.hasClass('flip90')) {
                label.removeClass('flip90');
                label.addClass('flip180');
            } else if (label.hasClass('flip180')) {
                label.removeClass('flip180');
                label.addClass('flip270');
            } else if (label.hasClass('flip270')) {
                label.removeClass('flip270');
            } else {
                label.addClass('flip90');
            }
        });


        switch (id) {
            case 1:
                label_button.css({
                    'margin-top': '90px'
                });
                label_container.css({
                    'margin-top': '90px'
                });
                break;

            case 2:
                label_button.css({
                    'margin-top': '90px'
                });
                label_container.css({
                    'margin-top': '90px'
                });
                $("#label_button_1").css({
                    top: $("#openseadragon-viewer-1").position().top + $('#openseadragon-rotator-1').height() + 5,
                    left: $("#openseadragon-viewer-1").position().left + $("#openseadragon-viewer-1").width() - 80,
                });

                $("#label_container_1").css({
                    top: $("#openseadragon-viewer-1").position().top + $('#openseadragon-rotator-1').height() + 5,
                    left: $("#openseadragon-viewer-1").position().left + $("#openseadragon-viewer-1").width() - 30 - $("#label_img_img-1").width(),
                });

                break;

            case 3:

                break;

            case 4:

                break;
        }
        $("#page").append(label_button);
        $("#page").append(label_container);



        v.open(image);

        $(element).mouseover(function () {
            currentFocus = id - 1;
            prevZoom = v.viewport.getZoom();
            prevPan = v.viewport.getCenter();
        });

        if (id > 1) {
            $("#slot-delete-" + id).show();
            $("#slot-delete-" + id).click(function () {
                var config = {
                    slides: []
                };
                for (let index = 0; index < openSlides.length; index++) {
                    if (id == index + 1) {
                        continue;
                    }
                    const slide = openSlides[index];
                    var center = viewers[index].viewport.getCenter();
                    config.slides.push({
                        id: slide.id,
                        center: {
                            x: center.x,
                            y: center.y
                        },
                        zoom: viewers[index].viewport.getZoom(),
                        rotation: viewers[index].viewport.getRotation()
                    });
                }
                var json = JSON.stringify(config);
                var url = new URL(window.location.href);
                if (url.searchParams.has('config')) {
                    url.searchParams.delete('config');
                }
                url.searchParams.append('config', json);

                window.location.href = url.href;
            });

            if (id == 3) {
                v.scalebar({
                    type: OpenSeadragon.ScalebarType.MICROSCOPY,
                    pixelsPerMeter: ppm,
                    minWidth: "160px",
                    location: OpenSeadragon.ScalebarLocation.BOTTOM_RIGHT,
                    yOffset: 40,
                    stayInsideImage: false,
                    color: "blue",
                    fontColor: "blue",
                    backgroundColor: "rgb(255, 255, 255, 0.8)",
                    fontSize: "large",
                    barThickness: 4
                });

            } else {
                v.scalebar({
                    type: OpenSeadragon.ScalebarType.MICROSCOPY,
                    pixelsPerMeter: ppm,
                    minWidth: "160px",
                    location: OpenSeadragon.ScalebarLocation.BOTTOM_LEFT,
                    yOffset: 40,
                    stayInsideImage: false,
                    color: "blue",
                    fontColor: "blue",
                    backgroundColor: "rgb(255, 255, 255, 0.8)",
                    fontSize: "large",
                    barThickness: 4
                });
            }
            v.addHandler('zoom', function () {
                if (currentFocus == id - 1 && syncLock) {
                    var currZoom = v.viewport.getZoom();
                    var delta = currZoom / prevZoom;
                    for (let index = 0; index < viewers.length; index++) {
                        if (index == currentFocus) continue;
                        const element = viewers[index];
                        element.viewport.zoomTo(element.viewport.getZoom() * delta);
                    }
                }

                if (currentFocus == id - 1) {
                    prevZoom = v.viewport.getZoom();
                }
            });

            v.addHandler('pan', function () {
                if (currentFocus == id - 1 && syncLock) {
                    var center = v.viewport.getCenter();
                    var delta = center.minus(prevPan);
                    var dPix = v.viewport.deltaPixelsFromPoints(delta);
                    for (let index = 0; index < viewers.length; index++) {
                        if (index == currentFocus) continue;
                        const element = viewers[index];
                        element.viewport.panBy(element.viewport.deltaPointsFromPixels(dPix));
                    }
                }


                if (currentFocus == id - 1) {
                    prevPan = v.viewport.getCenter();
                }
            });

            // v.addHandler('rotate', function () {
            //     if (currentFocus == id - 1 && syncLock) {
            //         var rot = v.viewport.getRotation();
            //         for (let index = 0; index < viewers.length; index++) {
            //             if (index == currentFocus) continue;
            //             const element = viewers[index];
            //             element.viewport.setRotation(rot);
            //         }
            //     }
            // });
        }
        return v;
    }

    // Helper Functions
    function updateRotation(deg) {
        viewer.viewport.setRotation(deg);
    }

    function resetZoomButtons() {
        $("#zoom-buttons").children().removeClass("btn-active");
    }

    function addOverlay(text, overlay) {
        // Add Tooltip with text
        overlay.annotation = text;
        if (text.length !== 0) {
            $(overlay.text).children(".card-content").children(".annotation-text").html(text);
            var newWidth = 100;
            if (text.length > 10) {
                newWidth = 150;
            }
            if (text.length > 20) {
                newWidth = 200;
            }
            $(overlay.text).css("width", newWidth + "px");
        }


        if (overlay.type == 'l') {
            updateLineCardDivText(overlay.text, overlay.line.firstSegment.point, overlay.line.lastSegment.point);
        } else if (overlay.type == 'r') {
            updateRectCardDivText(overlay.text, overlay.rect.strokeBounds.topLeft, overlay.rect.strokeBounds.topRight, overlay.rect.strokeBounds.bottomRight);
        } else if (overlay.type == 'c') {
            updateCircleCardDivText(overlay.text, overlay.circle.position.add(new Point(0, overlay.circle.radius + overlay.circle.strokeWidth)), overlay.circle.radius);
        }
        var editButton = $(overlay.text).children(".edit-button").get(0);
        var deleteButton = $(overlay.text).children(".delete-button").get(0);
        var confirmationModal = $("#delete-confirm").clone();
        $(confirmationModal).children(".modal-content").children(".card").css({
            "width": "300px",
            "margin": "auto"
        });
        $(confirmationModal).attr('id', '');
        $("#page").append(confirmationModal);
        $(deleteButton).click(function () {
            $(confirmationModal).addClass('is-active');
        });


        $(confirmationModal).children().find("#cancel-button").click(function () {
            $(confirmationModal).removeClass('is-active');
        });

        $(confirmationModal).children().find("#delete-button").click(function () {
            $(confirmationModal).removeClass('is-active');
            $(confirmationModal).remove();
            $(overlay.text).remove();
            $.post('/' + appname + '/annotation/delete/' + overlay.id);
            if (overlay.type == 'c') {
                overlay.circle.remove();
                var index;
                for (index = 0; index < circles.length; index++) {
                    var element = circles[index];
                    if (element.circle === overlay.circle) {
                        circles.splice(index, 1);
                        break;
                    }
                }

            } else if (overlay.type == 'r') {
                overlay.rect.remove();
                var i;
                for (i = 0; i < rects.length; i++) {
                    var e = rects[i];
                    if (e.rect === overlay.rect) {
                        rects.splice(i, 1);
                        break;
                    }
                }

            } else if (overlay.type == 'l') {
                overlay.line.remove();
                var j;
                for (j = 0; j < lines.length; j++) {
                    var e1 = lines[j];
                    if (e1.line === overlay.line) {
                        lines.splice(j, 1);
                        break;
                    }
                }

            }

        });

        $(editButton).click(function () {
            $("#annotation-modal-title").html("Edit Annotation");
            $("#annotation-modal").addClass("is-active");
            $("#annotation-save-btn").val(overlay.type + '-' + overlay.id);
            editMode = true;
            $("#annotation-text").val(overlay.annotation);
            currentEditingOverlay = overlay;
        });

        $(overlay.text).hover(function () {
            $(deleteButton).show();
            $(editButton).show();
            if (overlay.type == 'l') {
                updateLineCardDivText(overlay.text, overlay.line.firstSegment.point, overlay.line.lastSegment.point);
            } else if (overlay.type == 'r') {
                updateRectCardDivText(overlay.text, overlay.rect.strokeBounds.topLeft, overlay.rect.strokeBounds.topRight, overlay.rect.strokeBounds.bottomRight);
            } else if (overlay.type == 'c') {
                updateCircleCardDivText(overlay.text, overlay.circle.position.add(new Point(0, overlay.circle.radius + overlay.circle.strokeWidth)), overlay.circle.radius);
            }
        }, function () {
            $(deleteButton).hide();
            $(editButton).hide();
            if (overlay.type == 'l') {
                updateLineCardDivText(overlay.text, overlay.line.firstSegment.point, overlay.line.lastSegment.point);
            } else if (overlay.type == 'r') {
                updateRectCardDivText(overlay.text, overlay.rect.strokeBounds.topLeft, overlay.rect.strokeBounds.topRight, overlay.rect.strokeBounds.bottomRight);
            } else if (overlay.type == 'c') {
                updateCircleCardDivText(overlay.text, overlay.circle.position.add(new Point(0, overlay.circle.radius + overlay.circle.strokeWidth)), overlay.circle.radius);
            }
        });

    }

    function closeAnnotation() {
        $("canvas").removeClass('cursor-crosshair');
    }

    function loadAnnotations() {
        $.get('/' + appname + '/annotation/' + slideId, function (data, status) {
            data.annotations.forEach(function (annotation) {
                if (annotation.type == 'l') {
                    var l = {
                        id: annotation.id,
                        line: Path.importJSON(annotation.json),
                        annotation: annotation.text,
                        text: createDivText(),
                        type: 'l'
                    };
                    project.activeLayer.addChild(l.line);
                    addOverlay(l.annotation, l);
                    lines.push(l);
                } else if (annotation.type == 'r') {
                    var r = {
                        id: annotation.id,
                        rect: Shape.importJSON(annotation.json),
                        annotation: annotation.text,
                        text: createDivText(),
                        type: 'r'
                    };
                    $(r.text).css("width", "115px");
                    $(r.text).children(".card-content").children(".measurement").css("font-size", "0.65rem");
                    project.activeLayer.addChild(r.rect);
                    addOverlay(r.annotation, r);
                    rects.push(r);
                    r.rect.onMouseEnter = function () {
                        $("#page").addClass("cursor-move");
                    };
                    r.rect.onMouseLeave = function () {
                        $("#page").removeClass("cursor-move");
                    };
                } else if (annotation.type == 'c') {
                    var c = {
                        id: annotation.id,
                        circle: Shape.importJSON(annotation.json),
                        annotation: annotation.text,
                        text: createDivText(),
                        type: 'c'
                    };
                    $(c.text).css("width", "90px");
                    $(c.text).children(".card-content").children(".measurement").css("font-size", "0.65rem");
                    project.activeLayer.addChild(c.circle);
                    addOverlay(c.annotation, c);
                    circles.push(c);
                    c.circle.onMouseEnter = function () {
                        $("#page").addClass("cursor-move");
                    };
                    c.circle.onMouseLeave = function () {
                        $("#page").removeClass("cursor-move");
                    };
                }
            });
        });

    }

    function resetAnnotationModal() {
        $("#annotation-text").val('');
        $("#annotation-modal-title").html("Add Annotation");
    }

    function updateAnnotation(text) {
        currentEditingOverlay.annotation = text;
        $.post('/' + appname + '/annotation/edit/' + currentEditingOverlay.id, {
            text: text
        });
        if (text.length !== 0) {
            $(currentEditingOverlay.text).children(".card-content").children(".annotation-text").html(text);
            var newWidth = 100;
            if (text.length > 10) {
                newWidth = 150;
            }
            if (text.length > 20) {
                newWidth = 200;
            }
            $(currentEditingOverlay.text).css("width", newWidth + "px");
        } else {
            var nWidth = 70;
            if (currentEditingOverlay.type == 'r') {
                nWidth = 150;
            } else if (currentEditingOverlay.type == 'c') {
                nWidth = 100;
            }
            $(currentEditingOverlay.text).css("width", nWidth + "px");
        }
        if (currentEditingOverlay.type == 'l') {
            updateLineCardDivText(currentEditingOverlay.text, currentEditingOverlay.line.firstSegment.point, currentEditingOverlay.line.lastSegment.point);
        } else if (currentEditingOverlay.type == 'r') {
            updateRectCardDivText(currentEditingOverlay.text, currentEditingOverlay.rect.strokeBounds.topLeft, currentEditingOverlay.rect.strokeBounds.topRight, currentEditingOverlay.rect.strokeBounds.bottomRight);
        } else if (currentEditingOverlay.type == 'c') {
            var radius = currentEditingOverlay.circle.radius;
            updateCircleCardDivText(currentEditingOverlay.text, currentEditingOverlay.circle.position.add(new Point(0, radius + stroke_width)), currentEditingOverlay.circle.radius);
        }
    }

    // Event Handlers

    // Toolbar Buttons

    $("#zoomin-btn").click(function () {
        resetZoomButtons();
    });

    $("#zoomout-btn").click(function () {
        resetZoomButtons();
    });

    // Zoom Preset Buttons
    $(".zoom-button").click(function (e) {
        viewer.viewport.zoomTo(parseInt(e.target.value));
    });



    $("#screenshot-btn").click(function () {
        $(this).addClass("is-success");
        $("#loading-modal").addClass("is-active");

        $('.openseadragon-container div:nth-child(2)').hide();
        html2canvas($("#viewer-container").get(0)).then(function (canvas) {
            Canvas2Image.saveAsPNG(canvas);
            $("#loading-modal").removeClass("is-active");
            $('.openseadragon-container div:nth-child(2)').show();
            $("#screenshot-btn").removeClass("is-success");
        });
    });



    $("#btn-rotate-preset-1").click(function () {
        rotator.setValue(0);
        updateRotation(0);
        fixRotatorTooltip();
    });

    $("#btn-rotate-preset-2").click(function () {
        rotator.setValue(90);
        updateRotation(90);
        fixRotatorTooltip();
    });

    $("#btn-rotate-preset-3").click(function () {
        rotator.setValue(180);
        updateRotation(180);
        fixRotatorTooltip();
    });

    $("#rotation-selector-dropdown").hover(function () {
        $(this).addClass("is-active");
        $("#rotation-dropdown-button").css({
            'background-color': '#3298dc',
            'color': 'white'
        });
    }, function () {
        if (!rotating) {
            $(this).removeClass("is-active");
            $("#rotation-dropdown-button").css({
                'background-color': 'rgba(0, 0, 0, 0)',
                'color': '#363636'
            });
        }
    });

    // TODO: reactivate the functionality 
    $("#draw-menu-dropdown").hover(function () {
        $(this).addClass("is-active");
        $("#draw-button").css({
            'background-color': '#f14668',
            'color': 'white'
        });
    }, function () {
        if (!selectingColor) {
            $(this).removeClass("is-active");
            // TODO: Change to drawMode only 0
            if (drawMode === 0 || drawMode === 1) {
                $("#draw-button").css({
                    'background-color': 'rgba(0, 0, 0, 0)',
                    'color': '#363636'
                });
            }
        }
    });

    $.get("name", function (data) {

        $("#slot-1").html(data.name);
    });

    var addSlideEvent = function (event) {
        $('#slide-selector-container').empty();
        var slotId = event.target.id;
        var listSlides = [];
        var data = $.ajax({
            url: 'group',
            type: 'GET',
            async: false
        }).responseText;

        data = JSON.parse(data);
        for (let index = 0; index < data.slides.length; index++) {
            const element = data.slides[index];
            var opened = false;
            for (let index = 0; index < openSlides.length; index++) {
                const e = openSlides[index];
                if (e.id == element.id) {
                    opened = true;
                    break;
                }
            }
            if (opened) continue;
            var res = $.ajax({
                url: '/' + appname + '/slide/' + element.id + '/thumbnail',
                async: false,
                type: 'GET'
            }).responseText;

            var thumbnail = JSON.parse(res).thumbnail;
            listSlides.push({
                'id': element.id,
                'name': element.name,
                'thumbnail': thumbnail
            });
        }

        listSlides.forEach(function (slide) {
            var slideSelector = document.createElement('div');
            $(slideSelector).addClass('slide-selector');
            var img = document.createElement('img');
            $(img).attr('src', slide.thumbnail);
            $(slideSelector).append(img);
            var span = document.createElement('span');
            $(span).html(slide.name);
            $(slideSelector).append(span);
            $('#slide-selector-container').append(slideSelector);
            $(slideSelector).click(function () {
                viewers.push(createViewer('/' + appname + '/' + slide.id + '.dzi'));
                $('#' + slotId).removeClass('text-light');
                $('#' + slotId).addClass('is-selected');
                $('#' + slotId).off('click');
                $('#' + slotId).html(slide.name);
                openSlides.push({
                    'id': slide.id,
                    'slot': slotId,
                    'image': '/' + appname + '/' + slide.id + '.dzi'
                });
                $('#slide-selector-container').empty();
                $('#open-slide-modal').removeClass('is-active');
            });
        });

        $('#open-slide-modal').addClass('is-active');
    };




    $('.text-light').click(addSlideEvent);

    $("#open-slide-modal").find(".delete").click(function () {
        $('#slide-selector-container').empty();
        $('#open-slide-modal').removeClass('is-active');
    });

    $("#open-slide-dropdown").hover(function () {
        $(this).addClass("is-active");
        $("#open-slide-button").css({
            'background-color': '#f14668',
            'color': 'white'
        });
    }, function () {
        $(this).removeClass("is-active");
        $("#open-slide-button").css({
            'background-color': 'rgba(0, 0, 0, 0)',
            'color': '#363636'
        });
    });



    $("#line-button").click(function () {
        if (drawMode !== 1)
            changeDrawMode(1);
        else
            changeDrawMode(0);
    });

    $("#rect-button").click(function () {
        if (drawMode !== 2)
            changeDrawMode(2);
        else
            changeDrawMode(0);
    });

    $("#circle-button").click(function () {
        if (drawMode !== 3)
            changeDrawMode(3);
        else
            changeDrawMode(0);
    });

    $("#circle-button-20").click(function (event) {
        if (drawMode !== 4) {
            changeDrawMode(4);
            fixedCricleInit(view.viewToProject(new Point(event.clientX, event.clientY)), 1500);
        } else
            changeDrawMode(0);
    });

    $("#circle-button-40").click(function (event) {
        if (drawMode !== 5) {
            changeDrawMode(5);
            fixedCricleInit(view.viewToProject(new Point(event.clientX, event.clientY)), 800);
        } else
            changeDrawMode(0);
    });

    // Modal Control Events (Modal for annotation input)

    $(".annotation-modal-close ").click(function () {
        $("#annotation-modal").removeClass("is-active");
        if (!editMode) {
            if (lastOverlay.type == 'r') {
                lastOverlay.rect.remove();
            } else if (lastOverlay.type == 'c') {
                lastOverlay.circle.remove();
            } else if (lastOverlay.type == 'l') {
                lastOverlay.line.remove();
            }
            $(lastOverlay.text).remove();
        }
        editMode = false;
        resetAnnotationModal();
        closeAnnotation();
    });

    $("#annotation-save-btn").click(function (event) {
        $("#annotation-modal").removeClass("is-active");
        var text = $("#annotation-text").val();
        if (editMode) {
            updateAnnotation(text);
        } else {

        }
        editMode = false;
        closeAnnotation();
        resetAnnotationModal();
    });

    $("#border-width-input").on('change', function (event) {
        var height = event.target.value;
        $("#border-example").css("height", height);
    });

    $("#fullscreen-btn").click(function () {
        if (isFullScreen) {
            isFullScreen = false;
            $.fullscreen.exit();
        } else {
            isFullScreen = true;
            $('body').fullscreen();

        }

    });

    // Resize event
    window.onresize = function () {
        paperOverlay.resize();
        paperOverlay.resizecanvas();
        updateViewerPos();
        setTimeout(function () {
            if (viewer.viewport.getZoom() < viewer.viewport.getHomeZoom()) {
                viewer.viewport.zoomTo(viewer.viewport.getHomeZoom());
            }
            viewer.viewport.minZoomLevel = viewer.viewport.getHomeZoom();
        }, 100);
        lines.forEach(function (line) {
            updateLineCardDivText(line.text, line.line.firstSegment.point, line.line.lastSegment.point);
        });
        rects.forEach(function (rect) {
            updateRectCardDivText(rect.text, rect.rect.strokeBounds.topLeft, rect.rect.strokeBounds.topRight, rect.rect.strokeBounds.bottomRight);
        });
        circles.forEach(function (circle) {
            updateCircleCardDivText(circle.text, circle.circle.position.add(new Point(0, radius + stroke_width)), circle.circle.radius);
        });
    };


    function updateViewerPos() {
        var navbarHeight = $(".navbar").height();
        var pageHeight = $("#page").height();
        var id = viewers.length;

        setTimeout(function () {
            for (let index = 0; index < openSlides.length; index++) {
                var slideId = index + 1;
                $("#openseadragon-rotator-" + slideId).css({
                    top: $("#openseadragon-viewer-" + slideId).position().top,
                    left: $("#openseadragon-viewer-" + slideId).position().left + $("#openseadragon-viewer-" + slideId).width() - 100,
                });
            }
        }, 100);

        switch (id) {
            case 1:
                $("#openseadragon-viewer-1").height(pageHeight);
                break;

            case 2:
                $("#openseadragon-viewer-1").height(pageHeight);
                $("#openseadragon-viewer-2").height(pageHeight);

                break;

            case 3:
                $("#openseadragon-viewer-1").height(pageHeight);
                $("#openseadragon-viewer-2").height((pageHeight) / 2);
                $("#openseadragon-viewer-3").height((pageHeight) / 2);
                // $("#openseadragon-viewer-3").css({
                //     bottom: (pageHeight)+'px'
                // });

                break;

            case 4:
                $("#openseadragon-viewer-1").height((pageHeight) / 2);
                $("#openseadragon-viewer-2").height((pageHeight) / 2);
                $("#openseadragon-viewer-3").height((pageHeight) / 2);
                $("#openseadragon-viewer-4").height((pageHeight) / 2);
                // $("#openseadragon-viewer-4").css({
                //     bottom: (pageHeight)+'px'
                // });
                break;

        }
        for (let i = 1; i <= id; i++) {
            if (id == 1) {
                $("#label_button_1").css({
                    position: 'absolute',
                    'margin-top': 0,
                    top: $("#openseadragon-viewer-" + i).position().top,
                    left: $("#openseadragon-viewer-" + i).position().left + $("#openseadragon-viewer-" + i).width() - 80,
                });
                $("#label_container_1").css({
                    top: $("#openseadragon-viewer-" + i).position().top,
                    'margin-top': 0,
                    left: $("#openseadragon-viewer-" + i).position().left + $("#openseadragon-viewer-" + i).width() - 30 - $("#label_img_img-" + i).width(),
                });
            }
            $("#label_button_" + i).css({
                position: 'absolute',
                top: $("#openseadragon-viewer-" + i).position().top + $('#openseadragon-rotator-' + i).height() + 5,
                left: $("#openseadragon-viewer-" + i).position().left + $("#openseadragon-viewer-" + i).width() - 80,
            });
            $("#label_container_" + i).css({
                top: $("#openseadragon-viewer-" + i).position().top + $('#openseadragon-rotator-' + i).height() + 5,
                left: $("#openseadragon-viewer-" + i).position().left + $("#openseadragon-viewer-" + i).width() - 30 - $("#label_img_img-" + i).width(),
            });

        }


    }

    $(document).on('keydown', function (event) {
        // Escape key
        if (event.keyCode == 27) {
            if (isFullScreen) {
                isFullScreen = false;
                $.fullscreen.exit();

            }
        }
    });

    // Paperjs Drawing tool

    // Openseadragon Mouse events
    var mouseTracker = new OpenSeadragon.MouseTracker({
        element: viewer.canvas,
        pressHandler: pressHandler,
        dragHandler: dragHandler,
        dragEndHandler: dragEndHandler,
        scrollHandler: resetZoomButtons,
        moveHandler: moveHandler,
    });
    mouseTracker.setTracking(true);

    function moveHandler(event) {
        if (drawMode === 4 || drawMode === 5) {
            var transformedPoint = view.viewToProject(new Point(event.position.x, event.position.y));
            currentCircle.circle.position = transformedPoint;
        }
    }

    function pressHandler(event) {


        var transformedPoint = view.viewToProject(new Point(event.position.x, event.position.y));
        startPoint = transformedPoint;
        switch (drawMode) {
            case 0:
                hitTest = null;
                var tPoint = view.viewToProject(new Point(event.position.x, event.position.y));
                var hitTestResult = project.hitTest(tPoint);
                if (hitTestResult && hitTestResult.item instanceof Shape) {
                    if (hitTestResult.item.type == 'circle') {
                        circles.forEach(function (circle) {
                            if (circle.circle === hitTestResult.item) {
                                hitTest = circle;
                            }
                        });
                    } else if (hitTestResult.item.type == 'rectangle') {
                        rects.forEach(function (rect) {
                            if (rect.rect === hitTestResult.item) {
                                hitTest = rect;
                            }
                        });
                    }
                }
                break;
            case 1:
                linePressHandler();
                break;

            case 2:
                rectPressHandler();
                break;

            case 3:
                circlePressHandler();
                break;

            case 4:
                fixedCriclePressHandler();
                break;

            case 5:
                fixedCriclePressHandler();
                break;

        }
    }

    function dragHandler(event) {
        var tPoint = view.viewToProject(new Point(event.position.x, event.position.y));
        switch (drawMode) {
            case 0:
                if (hitTest) {
                    var tPoint1 = view.viewToProject(new Point(0, 0));
                    var tPoint2 = view.viewToProject(new Point(event.delta.x, event.delta.y));

                    if (hitTest.type == 'r') {
                        hitTest.rect.position = hitTest.rect.position.add(tPoint2.subtract(tPoint1));
                        updateRectCardDivText(hitTest.text, hitTest.rect.strokeBounds.topLeft, hitTest.rect.strokeBounds.topRight, hitTest.rect.strokeBounds.bottomRight);
                    } else if (hitTest.type == 'c') {
                        hitTest.circle.position = hitTest.circle.position.add(tPoint2.subtract(tPoint1));
                        var radius = hitTest.circle.radius;
                        updateCircleCardDivText(hitTest.text, hitTest.circle.position.add(new Point(0, radius + stroke_width)), radius);
                    }
                    viewer.setMouseNavEnabled(false);
                }
                break;
            case 1:
                lineDragHandler(tPoint);
                break;

            case 2:
                rectDragHandler(tPoint);
                break;

            case 3:
                circleDragHandler(tPoint);
                break;
        }
    }

    function dragEndHandler(event) {
        var tPoint = view.viewToProject(new Point(event.position.x, event.position.y));
        switch (drawMode) {
            case 0:
                if (hitTest) {
                    viewer.setMouseNavEnabled(true);
                    var json = '';
                    if (hitTest.type == 'l') {
                        json = hitTest.line.exportJSON();
                    } else if (hitTest.type == 'r') {
                        json = hitTest.rect.exportJSON();
                    } else if (hitTest.type == 'c') {
                        json = hitTest.circle.exportJSON();
                    }
                    $.post('/' + appname + '/annotation/edit/' + hitTest.id, {
                        json: json
                    });
                }
                hitTest = null;
                break;
            case 1:
                lineDragEndHandler(tPoint);
                break;

            case 2:
                rectDragEndHandler(tPoint);
                break;

            case 3:
                circleDragEndHandler(tPoint);
                break;
        }

        startPoint = null;
        changeDrawMode(0);

    }

    var pos = $('#filter-button').position();
    var pos_x = (pos.right) - ($('.draggle-menu').width() / 2);
    var pos_y = (pos.top) + 80;
    $(".draggle-menu").css({
        'top': pos_y ,
        'left': pos_x
    });
    
    $(".draggle-menu .draggle-menu-header .delete").on('click', function (e) {
        $(".draggle-menu").hide();
        var pos = $('#filter-button').position();
        var pos_x = (pos.right) - ($('.draggle-menu').width() / 2);
        var pos_y = (pos.top) + 80;
        $(".draggle-menu").css({
            'top': pos_y ,
            'left': pos_x
        });
    });

    $("#filter-button").on('click', function (e) {
        $(".draggle-menu").show();
    });

    // Make the DIV element draggable:
    var dragItem = document.querySelector(".draggle-menu");
    var dragItemHeader = document.querySelector(".draggle-menu-header");
    dragElement(dragItem);

    function dragElement(elmnt) {
        var pos1 = 0,
            pos2 = 0,
            pos3 = 0,
            pos4 = 0;
        if (dragItemHeader) {
            // if present, the header is where you move the DIV from:
            dragItemHeader.onmousedown = dragMouseDown;
        } else {
            // otherwise, move the DIV from anywhere inside the DIV:
            elmnt.onmousedown = dragMouseDown;
        }

        function dragMouseDown(e) {
            e = e || window.event;
            e.preventDefault();
            // get the mouse cursor position at startup:
            pos3 = e.clientX;
            pos4 = e.clientY;
            document.onmouseup = closeDragElement;
            // call a function whenever the cursor moves:
            document.onmousemove = elementDrag;
        }

        function elementDrag(e) {
            e = e || window.event;
            e.preventDefault();
            // calculate the new cursor position:
            pos1 = pos3 - e.clientX;
            pos2 = pos4 - e.clientY;
            pos3 = e.clientX;
            pos4 = e.clientY;
            // set the element's new position:
            elmnt.style.top = (elmnt.offsetTop - pos2) + "px";
            elmnt.style.left = (elmnt.offsetLeft - pos1) + "px";
        }

        function closeDragElement() {
            // stop moving when mouse button is released:
            document.onmouseup = null;
            document.onmousemove = null;
        }
    }


    // Helper function
    function linePressHandler() {
        currentLine = {
            line: new Path(),
            text: createDivText(),
        };
        currentLine.line.strokeColor = stroke_color;
        currentLine.line.fillColor = currentLine.line.strokeColor;
        currentLine.line.strokeWidth = stroke_width;
        currentLine.line.add(startPoint);
    }

    function lineDragHandler(current) {
        var firstSeg = currentLine.line.firstSegment;
        currentLine.line.removeSegments();
        currentLine.line.add(firstSeg, current);
        updateLineCardDivText(currentLine.text, current, firstSeg.point);
    }

    function lineDragEndHandler(current) {
        var dup = {
            line: currentLine.line.clone(),
            text: currentLine.text,
            id: null,
            annotation: '',
            type: 'l'
        };
        currentLine.line.remove();
        currentLine = null;

        lastOverlay = dup;
        lines.push(lastOverlay);
        addOverlay("", lastOverlay);
        $.post('/' + appname + '/annotation/add', {
            slideId: '' + slideId,
            Json: lastOverlay.line.exportJSON(),
            text: '',
            type: 'l'
        }, function (data) {
            lastOverlay.id = parseInt(data.id);
        });
    }

    function circlePressHandler() {
        currentCircle = {
            circle: null,
            text: createDivText(),
        };
        $(currentCircle.text).css("width", "90px");
        $(currentCircle.text).children(".card-content").children(".measurement").css("font-size", "0.65rem");
    }

    function circleDragHandler(current) {
        if (currentCircle.circle === null) {
            currentCircle.circle = createCircle(startPoint, startPoint.getDistance(current));
        }
        currentCircle.circle.remove();
        currentCircle.circle = createCircle(startPoint, startPoint.getDistance(current));

        var radius = currentCircle.circle.radius;
        updateCircleCardDivText(currentCircle.text, currentCircle.circle.position.add(new Point(0, radius + stroke_width)), radius);

    }

    function circleDragEndHandler(current) {
        if (currentCircle !== null) {
            var c = createCircle(currentCircle.circle.position, currentCircle.circle.radius);

            var obj = {
                id: null,
                type: 'c',
                circle: c,
                text: currentCircle.text
            };

            lastOverlay = obj;
            currentCircle.circle.remove();
            circles.push(lastOverlay);
            addOverlay("", lastOverlay);
            lastOverlay.circle.onMouseEnter = function () {
                $("#page").addClass("cursor-move");
            };
            lastOverlay.circle.onMouseLeave = function () {
                $("#page").removeClass("cursor-move");
            };
            $.post('/' + appname + '/annotation/add', {
                slideId: '' + slideId,
                Json: lastOverlay.circle.exportJSON(),
                text: '',
                type: 'c'
            }, function (data) {
                lastOverlay.id = parseInt(data.id);
            });
        }
    }

    function rectPressHandler() {
        currentRect = {
            rect: null,
            text: createDivText(),
        };
        $(currentRect.text).css("width", "115px");
        $(currentRect.text).children(".card-content").children(".measurement").css("font-size", "0.65rem");
    }

    function rectDragHandler(current) {
        if (currentRect.rect === null) {
            currentRect.rect = createRect(startPoint, current);
        }
        currentRect.rect.remove();
        currentRect.rect = createRect(startPoint, current);
        updateRectCardDivText(currentRect.text, currentRect.rect.strokeBounds.topLeft, currentRect.rect.strokeBounds.topRight, currentRect.rect.strokeBounds.bottomRight);
    }

    function rectDragEndHandler(current) {
        if (currentRect.rect !== null) {
            var finalRect = createRect(startPoint, current);
            var obj = {
                id: null,
                type: 'r',
                rect: finalRect,
                text: currentRect.text
            };
            lastOverlay = obj;
            currentRect.rect.remove();

            // Open annotation menu
            rects.push(lastOverlay);
            addOverlay("", lastOverlay);

            lastOverlay.rect.onMouseEnter = function () {
                $("#page").addClass("cursor-move");
            };
            lastOverlay.rect.onMouseLeave = function () {
                $("#page").removeClass("cursor-move");
            };
            $.post('/' + appname + '/annotation/add', {
                slideId: '' + slideId,
                Json: lastOverlay.rect.exportJSON(),
                text: '',
                type: 'r'
            }, function (data) {
                lastOverlay.id = parseInt(data.id);
            });
        }

    }

    function fixedCriclePressHandler(current) {
        if (currentCircle !== null) {
            var c = createCircle(currentCircle.circle.position, currentCircle.circle.radius);

            var obj = {
                id: null,
                type: 'c',
                circle: c,
                text: currentCircle.text
            };

            lastOverlay = obj;
            currentCircle.circle.remove();
            circles.push(lastOverlay);
            addOverlay("", lastOverlay);
            lastOverlay.circle.onMouseEnter = function () {
                $("#page").addClass("cursor-move");
            };
            lastOverlay.circle.onMouseLeave = function () {
                $("#page").removeClass("cursor-move");
            };
            $.post('/' + appname + '/annotation/add', {
                slideId: '' + slideId,
                Json: lastOverlay.circle.exportJSON(),
                text: '',
                type: 'c'
            }, function (data) {
                lastOverlay.id = parseInt(data.id);
            });
        }
        changeDrawMode(0);
    }


    function createCircle(center, radius) {
        var c = new Shape.Circle(center, radius);
        c.strokeColor = stroke_color;
        c.fillColor = 'rgba(255, 255, 255, 0.05)';
        c.strokeWidth = stroke_width;
        return c;
    }

    function fixedCricleInit(center, radius) {
        currentCircle = {
            circle: null,
            text: createDivText(),
        }
        $(currentCircle.text).css("width", "90px");
        $(currentCircle.text).children(".card-content").children(".measurement").css("font-size", "0.65rem");
        currentCircle.circle = new Shape.Circle(center, radius);
        currentCircle.circle.strokeColor = stroke_color;
        currentCircle.circle.fillColor = 'rgba(255, 255, 255, 0.05)';
        currentCircle.circle.strokeWidth = stroke_width;
    }

    function createRect(from, to) {
        var c = new Shape.Rectangle(from, to);
        c.strokeColor = stroke_color;
        c.fillColor = 'rgba(255, 255, 255, 0.05)';
        c.strokeWidth = stroke_width;
        return c;
    }

    function createDivText() {
        var card = document.createElement("div");
        $(card).width("70px");
        $(card).addClass("card");
        var deleteButton = document.createElement("button");
        $(deleteButton).addClass("card-control");
        $(deleteButton).addClass("delete-button");
        var delIcon = document.createElement("i");
        $(delIcon).addClass("fas");
        $(delIcon).addClass("fa-times");
        $(deleteButton).append(delIcon);

        var editButton = document.createElement("button");
        $(editButton).addClass("card-control");
        $(editButton).addClass("edit-button");
        var editIcon = document.createElement("i");
        $(editIcon).addClass("fas");
        $(editIcon).addClass("fa-edit");
        $(editButton).append(editIcon);
        $(card).append(deleteButton);
        $(card).append(editButton);

        $(editButton).hide();
        $(deleteButton).hide();

        var cardContent = document.createElement("div");
        $(cardContent).css({
            "padding": "0",
            "text-align": "center"
        });
        $(cardContent).addClass("card-content");
        $(card).append(cardContent);
        var p = document.createElement("p");
        $(p).addClass("measurement");
        var annote = document.createElement("p");
        $(annote).addClass("annotation-text");
        $(cardContent).append(annote);
        $(cardContent).append(p);
        $("#openseadragon-viewer-1").append(card);
        return card;
    }

    function updateLineCardDivText(card, start, end) {
        var rot = angleFromHorizontal(start, end);

        var content = converterToSI(start.getDistance(end));
        $(card).children(".card-content").children(".measurement").html(content);
        // If in first or third quadrand
        if ((end.x > start.x && end.y < start.y) || (end.x < start.x && end.y > start.y)) {
            rot = rot * -1;
        }
        var mid = midPoint(start, end).subtract(new Point(0, stroke_width));
        var pos = view.projectToView(mid);
        var textRot = rot * (Math.PI / 180.0);

        var w = ($(card).width() / 2.0);
        var h = $(card).height();
        var xOff = w * Math.cos(textRot) - h * Math.sin(textRot);
        var yOff = w * Math.sin(textRot) + h * Math.cos(textRot);

        var off = new Point(xOff, yOff);
        pos = pos.subtract(off);


        $(card).css({
            "position": "absolute",
            "top": pos.y,
            "left": pos.x,
            "transform-origin": "top left",
            "-ms-transform": "rotate(" + rot + "deg)",
            "transform": "rotate(" + rot + "deg)",
        });

    }

    function updateRectCardDivText(card, topLeft, topRight, bottomRight) {

        var content = converterToSI(topLeft.getDistance(topRight)) + "X" + converterToSI(topRight.getDistance(bottomRight));
        $(card).children(".card-content").children(".measurement").html(content);

        var mid = midPoint(topLeft, topRight);
        var pos = view.projectToView(mid);

        var w = ($(card).width() / 2.0);
        var h = $(card).height();

        var off = new Point(w, h);
        pos = pos.subtract(off);


        $(card).css({
            "position": "absolute",
            "top": pos.y,
            "left": pos.x,
        });

    }

    function updateCircleCardDivText(card, position, radius) {

        var content = "r=" + converterToSI(radius);
        $(card).children(".card-content").children(".measurement").html(content);

        var pos = view.projectToView(position);

        var w = ($(card).width() / 2.0);

        var off = new Point(w, 0);
        pos = pos.subtract(off);


        $(card).css({
            "position": "absolute",
            "top": pos.y,
            "left": pos.x,
        });

    }

    function converterToSI(val) {
        val = val / ppm;
        var unit = 'm';
        // Convert to mm 
        val = val * 1000.0;
        unit = '㎜';
        var test = parseInt(val * 1000);
        if (test.toString().length <= 2) {
            val = val * 1000.0;
            unit = '㎛';
            test = parseInt(val * 1000);
            if (test.toString().length <= 2) {
                val = val * 1000.0;
                unit = '㎚';
            }
        }
        val = val.toFixed(2);
        return val.toString() + unit;
    }

    function midPoint(a, b) {
        return new Point((a.x + b.x) / 2, (a.y + b.y) / 2);
    }

    function angleFromHorizontal(a, b) {
        var max = Point.max(a, b);
        var min = Point.min(a, b);
        var vec = max.subtract(min);

        return vec.getAngle(new Point(1, 0));
    }

    function changeDrawMode(mode) {
        // TODO: change Draw mode only to 0
        if (drawMode !== 1) {
            $("#draw-button").css({
                'background-color': 'rgba(0, 0, 0, 0)',
                'color': '#363636'
            });
        }
        $("#line-button").css({
            'color': '#363636',
            'background-color': 'rgba(0, 0, 0, 0)'
        });
        $("#rect-button").css({
            'color': '#363636',
            'background-color': 'rgba(0, 0, 0, 0)'
        });
        $("#circle-button").css({
            'color': '#363636',
            'background-color': 'rgba(0, 0, 0, 0)'
        });
        $("#circle-button-20").css({
            'color': '#363636',
            'background-color': 'rgba(0, 0, 0, 0)'
        });
        $("#circle-button-40").css({
            'color': '#363636',
            'background-color': 'rgba(0, 0, 0, 0)'
        });
        drawMode = mode;
        if (mode === 0) {
            viewer.setMouseNavEnabled(true);
            $("canvas").removeClass('cursor-crosshair');
        } else {
            viewer.setMouseNavEnabled(false);
            if (drawMode !== 1) {
                $("#draw-button").css({
                    'background-color': '#f14668',
                    'color': 'white'
                });
            }
            $("canvas").addClass('cursor-crosshair');
            if (mode === 1) {
                $("#line-button").css({
                    'color': 'white',
                    'background-color': 'hsl(141, 53%, 53%)'
                });
            } else if (mode === 2) {
                $("#rect-button").css({
                    'color': 'white',
                    'background-color': 'hsl(141, 53%, 53%)'
                });
            } else if (mode === 3) {
                $("#circle-button").css({
                    'color': 'white',
                    'background-color': 'hsl(141, 53%, 53%)'
                });
            } else if (mode === 4) {
                $("#circle-button-20").css({
                    'color': 'white',
                    'background-color': 'hsl(141, 53%, 53%)'
                });
            } else if (mode === 5) {
                $("#circle-button-40").css({
                    'color': 'white',
                    'background-color': 'hsl(141, 53%, 53%)'
                });
            }
        }

        if (currentCircle !== null) {
            currentCircle.circle.remove();
        }
    }


    // SLIDE TRAY FUNCTIONALTIY
    $("#slide-tray-large-button").click(function () {
        slideTrayPercent = 0.25;
        $(this).css({
            'background-image': "url('/static/images/SlideTrayLargeBtnPressed.png')"
        });
        $("#slide-tray-med-button").css({
            'background-image': "url('/static/images/SlideTrayMedBtn.png')"
        });
        $("#slide-tray-small-button").css({
            'background-image': "url('/static/images/SlideTraySmallBtn.png')"
        });

        $(".slide-tray-item .slide-tray-image").show();

        $(".slide-tray-item .slide-tray-image").css({
            'height': 'calc(90% - 2px)'
        });

        $(".slide-tray-item .slide-tray-title").css({
            'font-size': '12px',
            'margin-bottom': '2px'
        });
        $(".slide-tray-barcode").hide();
        $(".slide-tray-label").show();


        $("#slide-tray-container").animate({
            'height': slideTrayLargeSize + 'px',
        }, 'fast');
    });

    $("#slide-tray-med-button").click(function () {
        slideTrayPercent = 0.2;
        $(this).css({
            'background-image': "url('/static/images/SlideTrayMedBtnPressed.png')"
        });
        $("#slide-tray-large-button").css({
            'background-image': "url('/static/images/SlideTrayLargeBtn.png')"
        });
        $("#slide-tray-small-button").css({
            'background-image': "url('/static/images/SlideTraySmallBtn.png')"
        });

        $(".slide-tray-item .slide-tray-image").show();

        $(".slide-tray-item .slide-tray-image").css({
            'height': 'calc(85% - 4px)'
        });

        $(".slide-tray-item .slide-tray-title").css({
            'font-size': '10px',
            'margin-bottom': '4px'
        });
        $(".slide-tray-barcode").show();
        $(".slide-tray-label").hide();

        $("#slide-tray-container").animate({
            'height': slideTrayMedSize + 'px',
        }, 'fast');
    });

    $("#slide-tray-small-button").click(function () {
        slideTrayPercent = 0.1;
        $(this).css({
            'background-image': "url('/static/images/SlideTraySmallBtnPressed.png')"
        });
        $("#slide-tray-med-button").css({
            'background-image': "url('/static/images/SlideTrayMedBtn.png')"
        });
        $("#slide-tray-large-button").css({
            'background-image': "url('/static/images/SlideTrayLargeBtn.png')"
        });


        $(".slide-tray-item .slide-tray-image").hide();

        $(".slide-tray-item .slide-tray-title").css({
            'font-size': '12px',
            'margin-bottom': '0px'
        });
        $(".slide-tray-barcode").hide();
        $(".slide-tray-label").hide();


        $("#slide-tray-container").animate({
            'height': slideTraySmallSize + 'px',
        }, 'fast');
    });

    $(".new-slide-modal-close").click(function () {
        $("#new-slide-modal").removeClass("is-active");
    });

    function initializeSlideTray() {
        var listSlides = [];
        $(".slide-tray-item").hide();
        $.get('group', function (data) {
            var slideItemTemplate = '<div class="slide-tray-item"><div class="slide-tray-title">Title</div><div class="slide-tray-image"></div></div>';
            data.slides.sort((a, b) => {
                if (a.name.includes("HE")) return 1;
                if (b.name.includes("HE")) return 1;
                return a.name.localeCompare(b.name);
            });
            for (let index = 0; index < data.slides.length; index++) {
                const element = data.slides[index];
                var slideItem = $(slideItemTemplate).clone();
                slideItem.find(".slide-tray-title").attr('title', element.name);
                if (element.name.length > 27) {
                    element.name = element.name.substring(0, 27) + '...';
                }
                element.slideItem = slideItem;
                slideItem.find(".slide-tray-title").html(element.name);
                $("#slide-tray").append(slideItem);
                openSlides.forEach(function (s) {
                    if (element.id == s.id) {
                        slideItem.css({
                            'background-color': '#99ff99'
                        });
                    }
                });

                listSlides.push(element);
            }


            $(".slide-tray-item").show();

            $('#slide-tray').slick({
                infinite: true,
                slidesToShow: 9,
                slidesToScroll: 9,
                prevArrow: '<button type="button" id="slide-tray-nav-button-left"><i class="fas fa-caret-left fa-3x"></i></button>',
                nextArrow: '<button type="button" id="slide-tray-nav-button-right"><i class="fas fa-caret-right fa-3x"></i></button>',
                dots: false,

            });


            // url: '/'+appname+'/slide/' + element.id + '/thumbnail,
            listSlides.forEach(function (slide) {
                slide.slideItem.click(function () {
                    var found = false;
                    openSlides.forEach(function (s) {
                        if (slide.id == s.id) {
                            found = true;
                        }
                    });
                    if (!found) {
                        $("#new-slide-modal").addClass("is-active");
                        $("#open-new-slide-new-button").off();
                        $("#open-new-slide-new-button").click(function () {
                            openNewSlideNewWindow(slide.id);
                            $("#new-slide-modal").removeClass("is-active");
                        });

                        $("#open-new-slide-same-button").off();
                        $("#open-new-slide-same-button").click(function () {
                            openNewSlideSameWindow(slide.id);
                            $("#new-slide-modal").removeClass("is-active");
                        });
                        $("#open-new-slide-parallel-button").off();
                        if (viewers.length >= 4) {
                            $("#open-new-slide-parallel-button").attr("disabled", true);
                        } else {
                            $("#open-new-slide-parallel-button").click(function () {
                                openNewSlideParallelView(slide);
                                $("#new-slide-modal").removeClass("is-active");
                            });
                        }
                    }
                });
                var img = new Image();

                img.onload = function () {
                    var width = this.width;
                    var height = this.height;
                    var ratio = 73 / width;
                    height = ratio * height;
                    $(this).width(73);
                    $(this).height(height);

                };

                img.src = "../" + slide.id + "/fullthumbnail";
                $(img).addClass("slide-tray-label");

                var barcode = new Image();
                barcode.onload = function () {
                    var width = this.width;
                    var height = this.height;
                    var ratio = 73 / width;
                    height = ratio * height;
                    $(this).width(73);
                    $(this).height(height);
                };
                barcode.src = "../" + slide.id + "/barcode";
                $(barcode).addClass("slide-tray-barcode");
                $(barcode).hide();
                slide.slideItem.find(".slide-tray-image").append(img);
                slide.slideItem.find(".slide-tray-image").append(barcode);
                slide.slideItem.find(".slide-tray-image").css({
                    'background': 'white'
                });
            });
        });
    }


    initializeSlideTray();

    $("#slide-tray-hide-button").click(function () {
        var pageHeight = $("#page").height();
        var containerHeight = $("#slide-tray-container").height();
        $("#slide-tray-container").animate({
            'bottom': (-1 * containerHeight - 20) + 'px'
        }, complete = function () {
            $("#slide-tray-show-button").show();
            $("#slide-tray-hide-button").hide();
        });
    });


    $("#slide-tray-show-button").click(function () {
        $("#slide-tray-show-button").hide();
        $("#slide-tray-hide-button").show();
        $("#slide-tray-container").animate({
            'bottom': '0'
        });
    });

    $("#slide-tray-show-button").hide();


    function openNewSlideSameWindow(id) {
        window.location.href = '/' + appname + '/slide/' + id;
    }

    function openNewSlideNewWindow(id) {
        window.open('/' + appname + '/slide/' + id, "_blank");
    }

    function openNewSlideParallelView(slide) {
        if (viewers.length < 4) {
            viewers.push(createViewer('/' + appname + '/' + slide.id + '.dzi'));
            $('#slot-' + viewers.length).removeClass('text-light');
            $('#slot-' + viewers.length).addClass('is-selected');
            $('#slot-' + viewers.length).off('click');
            $('#slot-' + viewers.length).html(slide.name);
            openSlides.push({
                'id': slide.id,
                'slot': 'slot-' + viewers.length,
                'image': '/' + appname + '/' + slide.id + '.dzi'
            });
            slide.slideItem.css({
                'background-color': '#99ff99'
            });
            slide.slideItem.off();
        }
    }

    function getProperties() {
        $.get('/' + appname + '/slide/' + openSlides[0].id + '/property', function (data) {
            console.log(data);
        });
    }


    getProperties();

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

});