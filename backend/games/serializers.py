from rest_framework import serializers
from .models import Game


class GameSerializer(serializers.ModelSerializer):
    """游戏序列化器"""
    
    final_price = serializers.ReadOnlyField()
    
    class Meta:
        model = Game
        fields = [
            'id', 'steam_id', 'name', 'description', 'price', 'currency', 
            'discount_percent', 'final_price', 'header_image', 'screenshots',
            'developer', 'publisher', 'release_date', 'tags', 'review_score',
            'review_count', 'platforms', 'languages', 'is_free', 'is_new',
            'created_at', 'updated_at', 'scraped_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class GameListSerializer(serializers.ModelSerializer):
    """游戏列表序列化器（简化版）"""
    
    final_price = serializers.ReadOnlyField()
    
    class Meta:
        model = Game
        fields = [
            'id', 'steam_id', 'name', 'price', 'currency', 'discount_percent',
            'final_price', 'header_image', 'developer', 'release_date',
            'review_score', 'is_free', 'is_new', 'scraped_at'
        ] 