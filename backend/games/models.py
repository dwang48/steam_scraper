from django.db import models
from django.utils import timezone


class Game(models.Model):
    """Steam游戏模型"""
    
    # 基础信息
    steam_id = models.CharField(max_length=20, unique=True, verbose_name="Steam ID")
    name = models.CharField(max_length=200, verbose_name="游戏名称")
    description = models.TextField(blank=True, verbose_name="游戏描述")
    
    # 价格信息
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="价格")
    currency = models.CharField(max_length=10, default="USD", verbose_name="货币")
    discount_percent = models.IntegerField(default=0, verbose_name="折扣百分比")
    
    # 媒体信息
    header_image = models.URLField(blank=True, verbose_name="头图链接")
    screenshots = models.JSONField(default=list, blank=True, verbose_name="截图列表")
    
    # 游戏详情
    developer = models.CharField(max_length=200, blank=True, verbose_name="开发商")
    publisher = models.CharField(max_length=200, blank=True, verbose_name="发行商")
    release_date = models.DateField(null=True, blank=True, verbose_name="发布日期")
    tags = models.JSONField(default=list, blank=True, verbose_name="标签")
    
    # 评分信息
    review_score = models.IntegerField(null=True, blank=True, verbose_name="评分")
    review_count = models.IntegerField(default=0, verbose_name="评论数量")
    
    # 系统信息
    platforms = models.JSONField(default=list, blank=True, verbose_name="支持平台")
    languages = models.JSONField(default=list, blank=True, verbose_name="支持语言")
    
    # 时间戳
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    scraped_at = models.DateTimeField(default=timezone.now, verbose_name="抓取时间")
    
    # 状态
    is_free = models.BooleanField(default=False, verbose_name="是否免费")
    is_new = models.BooleanField(default=True, verbose_name="是否新游戏")
    
    class Meta:
        db_table = 'games'
        verbose_name = "游戏"
        verbose_name_plural = "游戏"
        ordering = ['-scraped_at', '-created_at']
        
    def __str__(self):
        return f"{self.name} (Steam ID: {self.steam_id})"
    
    @property
    def final_price(self):
        """计算最终价格（考虑折扣）"""
        if self.price and self.discount_percent:
            return float(self.price) * (100 - self.discount_percent) / 100
        return float(self.price) if self.price else 0 