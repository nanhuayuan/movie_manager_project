# app/services/media_manager.py
from abc import ABC, abstractmethod
from app.core.exceptions import *
from app.utils.jellyfin_util import JellyfinUtil
from app.services.chart_service import ChartService
from app.utils.everything_utils import EverythingUtils
from concurrent.futures import ThreadPoolExecutor
from app.config.log_config import info, error, debug


class DuplicateDetectionStrategy(ABC):
    @abstractmethod
    def is_duplicate(self, current_movie, reference_movie):
        """Check if movies are duplicates"""
        pass


class SerialNumberStrategy(DuplicateDetectionStrategy):
    def is_duplicate(self, current_movie, reference_movie):
        if not reference_movie:
            return False

        current_serial = current_movie.name.split(".")[0]
        reference_serial = reference_movie.name.split(".")[0]
        return current_serial == reference_serial


class MediaQualityAnalyzer:
    def analyze(self, movie_details):
        """Analyze media quality"""
        quality_score = 0

        # Check if from verified source
        if '250' in movie_details.media_sources[0].path:
            quality_score += 50

        # Check file size (larger usually means better quality)
        size_gb = movie_details.media_sources[0].size / 1073741824
        if size_gb > 4:
            quality_score += 30
        elif size_gb > 2:
            quality_score += 20

        # Check storage location preference
        if 'CACHEDEV1_DATA' not in movie_details.media_sources[0].path:
            quality_score += 10

        return quality_score


class MediaManager:
    def __init__(self):
        self.jellyfin = JellyfinUtil()
        self.chart_service = ChartService()
        self.everything = EverythingUtils()
        self.quality_analyzer = MediaQualityAnalyzer()
        self.duplicate_detector = SerialNumberStrategy()

    def add_charts_to_db(self):
        """Add charts to database"""
        try:
            info("Starting chart processing")
            charts = self.chart_service.parse_local_chartlist()
            if not charts:
                raise ResourceNotFoundError("No charts found")

            info(f"Found {len(charts)} charts")
            for chart in charts:
                self._process_chart(chart)

        except Exception as e:
            error(f"Error processing charts: {str(e)}")
            raise ProcessingError(f"Chart processing failed: {str(e)}")

    def update_playlists(self):
        """Update playlists with chart entries"""
        try:
            charts = self.chart_service.parse_local_chartlist()
            if not charts:
                raise ResourceNotFoundError("No charts found")

            with ThreadPoolExecutor() as executor:
                executor.map(self._update_playlist, charts)

        except Exception as e:
            error(f"Error updating playlists: {str(e)}")
            raise ProcessingError(f"Playlist update failed: {str(e)}")

    def remove_duplicates(self):
        """Remove duplicate media files"""
        try:
            movies = self.jellyfin.get_all_movie_info()
            processed = {}

            for movie in movies:
                details = self.jellyfin.get_movie_details(movie.id)

                for processed_id, processed_details in processed.items():
                    if self.duplicate_detector.is_duplicate(details, processed_details):
                        self._handle_duplicate(details, processed_details)
                        break

                processed[movie.id] = details

        except Exception as e:
            error(f"Error removing duplicates: {str(e)}")
            raise ProcessingError(f"Duplicate removal failed: {str(e)}")

    def cleanup_missing_files(self):
        """Remove entries for missing files"""
        try:
            movies = self.jellyfin.get_all_movie_info()

            for movie in movies:
                if not self.everything.search_movie(movie.name):
                    info(f"Removing missing movie: {movie.name}")
                    self.jellyfin.delete_movie_by_id(movie.id)

        except Exception as e:
            error(f"Error cleaning up missing files: {str(e)}")
            raise ProcessingError(f"Cleanup failed: {str(e)}")

    def _process_chart(self, chart):
        """Process single chart"""
        info(f"Processing chart: {chart.name}")

        for entry in chart.entries:
            try:
                self._process_chart_entry(entry)
            except Exception as e:
                error(f"Error processing entry {entry.serial_number}: {str(e)}")

    def _process_chart_entry(self, entry):
        """Process single chart entry"""
        debug(f"Processing entry: {entry.serial_number}")

        if movie_id := self.jellyfin.get_one_id_by_serial_number_search(entry.serial_number):
            playlist_id = self.jellyfin.get_playlist_id(entry.chart_name)
            self.jellyfin.add_to_playlist(playlist_id, movie_id)
            info(f"Added {entry.serial_number} to playlist {entry.chart_name}")
        else:
            warning(f"Movie not found: {entry.serial_number}")

    def _handle_duplicate(self, current_details, reference_details):
        """Handle duplicate movies"""
        current_score = self.quality_analyzer.analyze(current_details)
        reference_score = self.quality_analyzer.analyze(reference_details)

        if current_score > reference_score:
            self.jellyfin.delete_movie_by_id(reference_details.id)
            info(f"Removed lower quality duplicate: {reference_details.name}")
        else:
            self.jellyfin.delete_movie_by_id(current_details.id)
            info(f"Removed lower quality duplicate: {current_details.name}")