from django.templatetags.static import static


def profile_avatar(request):
    """Expose a resolved avatar URL to every template."""
    if not request.user.is_authenticated:
        return {'topbar_avatar_url': static('Defaults/Default_profile.jpg')}

    try:
        profile = request.user.profile
        image_name = (profile.image.name or '').replace('\\', '/')
        if image_name and image_name != 'Defaults/Default-profile.jpg':
            if image_name.startswith('User_Icons/'):
                url = static(image_name)
            else:
                url = profile.image.url
        else:
            url = static('Defaults/Default_profile.jpg')
    except Exception:
        url = static('Defaults/Default_profile.jpg')

    return {'topbar_avatar_url': url}
