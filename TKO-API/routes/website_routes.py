from flask import Blueprint, render_template

website_bp = Blueprint("website", __name__)

@website_bp.route("/chromaglow")
@website_bp.route("/chromaglow/")
def chromaglow_home():
    return render_template("chromaglow/home.html")


@website_bp.route("/chromaglow/about")
def chromaglow_about():
    return render_template("chromaglow/about.html")


@website_bp.route("/chromaglow/art")
def chromaglow_art():
    return render_template("chromaglow/art.html")


@website_bp.route("/chromaglow/lessons")
def chromaglow_lessons():
    return render_template("chromaglow/lessons.html")


@website_bp.route("/chromaglow/links")
def chromaglow_links():
    return render_template("chromaglow/links.html")


@website_bp.route("/chromaglow/merch")
def chromaglow_merch():
    return render_template("chromaglow/merch.html")


@website_bp.route("/chromaglow/music")
def chromaglow_music():
    return render_template("chromaglow/music.html")


@website_bp.route("/chromaglow/memory-room")
def chromaglow_memoryroom():
    return render_template("chromaglow/memory_room.html")


@website_bp.route("/")
@website_bp.route("/home")
@website_bp.route("/home/")
def tko_home():
    return render_template("index.html")


@website_bp.route("/about")
@website_bp.route("/about/")
def tko_about():
    return render_template("about.html")


@website_bp.route("/music")
@website_bp.route("/music/")
def tko_music():
    return render_template("music.html")


@website_bp.route("/forum")
@website_bp.route("/forum/")
def tko_forum():
    return render_template("community.html")


@website_bp.route("/sammi")
@website_bp.route("/sammi/")
def tko_sammi():
    return render_template("portfolio.html")


@website_bp.route("/newsletter")
@website_bp.route("/newsletter/")
def tko_newsletter():
    return render_template("newsletter.html.html")
