from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q
from .models import Game
from .serializers import GameSerializer, GameListSerializer


class GameViewSet(viewsets.ModelViewSet):
    """游戏API视图集"""
    
    queryset = Game.objects.all()
    serializer_class = GameSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_free', 'is_new', 'currency']  # 移除了platforms，因为它是JSONField
    search_fields = ['name', 'developer', 'publisher']  # 移除了tags，因为它是JSONField
    ordering_fields = ['price', 'release_date', 'review_score', 'scraped_at', 'created_at']
    ordering = ['-scraped_at']
    
    def get_serializer_class(self):
        """根据action选择序列化器"""
        if self.action == 'list':
            return GameListSerializer
        return GameSerializer
    
    @action(detail=False, methods=['get'])
    def new_games(self, request):
        """获取新游戏列表"""
        new_games = self.queryset.filter(is_new=True)
        page = self.paginate_queryset(new_games)
        if page is not None:
            serializer = GameListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = GameListSerializer(new_games, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def free_games(self, request):
        """获取免费游戏列表"""
        free_games = self.queryset.filter(is_free=True)
        page = self.paginate_queryset(free_games)
        if page is not None:
            serializer = GameListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = GameListSerializer(free_games, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def on_sale(self, request):
        """获取打折游戏列表"""
        sale_games = self.queryset.filter(discount_percent__gt=0)
        page = self.paginate_queryset(sale_games)
        if page is not None:
            serializer = GameListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = GameListSerializer(sale_games, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """获取统计信息"""
        total_games = self.queryset.count()
        new_games = self.queryset.filter(is_new=True).count()
        free_games = self.queryset.filter(is_free=True).count()
        on_sale = self.queryset.filter(discount_percent__gt=0).count()
        
        return Response({
            'total_games': total_games,
            'new_games': new_games,
            'free_games': free_games,
            'on_sale': on_sale,
        }) 