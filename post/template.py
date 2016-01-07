# -*- coding: utf-8 -*-

TEMPLATE = u"""<!doctype html>
<html class="no-js" lang="">
    <head>
        <meta charset="utf-8">
        <title>{title}</title>
        <link href="https://fonts.googleapis.com/css?family=Open+Sans:400,700,600,400italic" rel="stylesheet" type="text/css" />
        <meta name="description" content="">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
        {style}
    </head>
    <body>
        <div class="luno-editor">
            {content}
        </div>
    </body>
</html>
"""

TEMPLATE_STYLE = u"""
<style type="text/css">
    /* reset */

    html, body, div, span, applet, object, iframe,
    h1, h2, h3, h4, h5, h6, p, blockquote, pre,
    a, abbr, acronym, address, big, cite, code,
    del, dfn, em, img, ins, kbd, q, s, samp,
    small, strike, strong, sub, sup, tt, var,
    b, u, i, input, center,
    dl, dt, dd, ol, ul, li,
    fieldset, form, label, legend,
    table, caption, tbody, tfoot, thead, tr, th, td,
    article, aside, canvas, details, embed,
    figure, figcaption, footer, header, hgroup,
    menu, nav, output, ruby, section, summary,
    time, mark, audio, video {
        margin: 0;
        padding: 0;
        border: 0;
        font-size: 100%;
        font: inherit;
        vertical-align: baseline;
    }

    /* HTML5 display-role reset for older browsers */
    article, aside, details, figcaption, figure,
    footer, header, hgroup, menu, nav, section {
        display: block;
    }

    body {
        line-height: 1;
    }

    ol, ul {
        list-style: none;
    }

    blockquote, q {
        quotes: none;
    }

    blockquote:before, blockquote:after,

    q:before, q:after {
        content: '';
        content: none;
    }

    table {
        border-collapse: collapse;
        border-spacing: 0;
    }

    caption, th, td {
        text-align: left;
        font-weight: normal;
    }
    /* Actual */

    html, body {
        font-size: 10px;
        font-family: "Open Sans", sans-serif;
    }

    /* Editor */
    .luno-editor {
        padding: 0 15px;
    }

    .luno-editor a {
        background-color: transparent;
        background-image: linear-gradient(to bottom, rgba(122, 142, 255, 0) 50%, rgba(122, 142, 255, 0.6) 50%);
        background-repeat: repeat-x;
        background-size: 2px 2px;
        background-position: 0 22px;
        color: rgb(122, 142, 255);
        text-decoration: none;
        word-wrap: break-word;
        -webkit-tap-highlight-color: rgba(122, 142, 255, 0.3);
    }

    .luno-editor a.hashtag {
        background-image: none;
        cursor: pointer;
        word-wrap: break-word;
    }

    .luno-editor a[data-trix-attachment] {
        background-image: none;
        color: inherit;
        cursor: pointer;
        display: block;
        max-width: 100%;
        text-align: center;
        text-decoration: none;
        width: 100%;
    }

    .luno-editor a[data-trix-attachment]:hover, .luno-editor a[data-trix-attachment]:visited:hover {
        color: inherit;
    }

    .luno-editor b, .luno-editor strong {
        font-weight: bold;
    }

    .luno-editor blockquote {
        border-left: 3px solid rgba(0,0,0,0.8);
        font-weight: 400;
        font-style: italic;
        font-size: 18px;
        line-height: 1.58;
        letter-spacing: -0.003em;
        padding-left: 20px;
        margin-left: -23px;
        padding-bottom: 3px;
    }

    .luno-editor em, .luno-editor i {
        font-style: italic;
    }

    .luno-editor *:first-child {
        margin-top: 0;
    }

    .luno-editor, .luno-editor div, .luno-editor p {
        color: rgba(0, 0, 0, 0.8);
        font-weight: 400;
        font-style: normal;
        font-size: 18px;
        line-height: 1.68;
        letter-spacing: -0.003em;
    }

    .luno-editor ul+div,
    .luno-editor ol+div,
    .luno-editor pre+div,
    .luno-editor blockquote+div {
        margin-top: 28px;
    }

    .luno-editor ul, .luno-editor ol {
        counter-reset: post;
        margin-top: 28px;
    }

    .luno-editor li {
        font-size: 18px;
        font-style: normal;
        letter-spacing: .01rem;
        line-height: 1.58;
        margin-left: 30px;
    }

    .luno-editor ol>li:before {
        counter-increment: post;
        content: counter(post) ".";
        font-feature-settings: "liga" on,"lnum" on;
        padding-right: 12px;
        text-rendering: optimizeLegibility;
        -moz-osx-font-smoothing: grayscale;
        -moz-font-feature-settings: "liga" on,"lnum" on;
        -webkit-font-feature-settings: "liga" on,"lnum" on;
        -webkit-font-smoothing: antialiased;
    }

    .luno-editor li:before {
        box-sizing: border-box;
        display: inline-block;
        font-size: 18px;
        margin-left: -58px;
        position: absolute;
        text-align: right;
        width: 58px;
    }

    .luno-editor ul > li::before {
        content: "•";
        padding-top: 4px;
        padding-right: 15px;
    }

    .luno-editor pre,
    .luno-editor code,
    .luno-editor kbd,
    .luno-editor samp {
        background: rgba(0,0,0,0.05);
        font-family: monospace;
        font-size: 16px;
        line-height: 22px;
        margin-top: 28px;
        overflow: auto;
        padding: 20px;
        white-space: pre-wrap;
    }

    /* Attachments */

    .luno-editor .attachment {
        color: rgba(0, 0, 0, 0.5);
        display: inline-block;
        font-size: 13px;
        margin: 0;
        margin-top: 28px;
        line-height: 1;
        padding: 0;
        position: relative;
        text-align: center;
        width: 100%;
    }

    .luno-editor a[data-trix-attachment] .attachment {
        width: initial;
    }

    .luno-editor .attachment.attachment-file {
        line-height: 30px;
    }

    .luno-editor .attachment .caption {
        display: inline-block;
        margin: 4px auto 0 auto;
        max-width: 100%;
        padding: 0 16px;
        text-align: center;
        vertical-align: bottom;
    }

    .luno-editor .attachment.attachment-preview .caption {
        display: block;
        margin-top: 8px;
    }

    .luno-editor .attachment:not(.attachment-preview) .caption {
        background-color: #fff;
        background-image: url(data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSI0OCIgaGVpZ2h0PSI0OCIgdmlld0JveD0iMCAwIDQ4IDQ4Ij48cGF0aCBkPSJNMzMgMTJ2MjNjMCA0LjQyLTMuNTggOC04IDhzLTgtMy41OC04LThWMTBjMC0yLjc2IDIuMjQtNSA1LTVzNSAyLjI0IDUgNXYyMWMwIDEuMS0uODkgMi0yIDItMS4xMSAwLTItLjktMi0yVjEyaC0zdjE5YzAgMi43NiAyLjI0IDUgNSA1czUtMi4yNCA1LTVWMTBjMC00LjQyLTMuNTgtOC04LThzLTggMy41OC04IDh2MjVjMCA2LjA4IDQuOTMgMTEgMTEgMTFzMTEtNC45MiAxMS0xMVYxMmgtM3oiIGZpbGw9IiM3YzdiN2IiIC8+PC9zdmc+);
        background-position: 8.5px center;
        background-repeat: no-repeat;
        background-size: 30px;
        border: 1px solid #ddd;
        border-radius: 3px;
        padding: 10px 10px 10px 50px;
        text-align: left;
    }

    .luno-editor .attachment .caption .size {
        display: none;
    }

    .luno-editor .attachment img {
        height: 100%;
        max-width: 100%;
        object-fit: contain;
    }
</style>
"""
