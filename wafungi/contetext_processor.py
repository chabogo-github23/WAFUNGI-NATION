from .models import Genre, Instrument

def common_data(request):
    """Add common data to all templates"""
    return {
        'all_genres': Genre.objects.all(),
        'all_instruments': Instrument.objects.all(),
    }
