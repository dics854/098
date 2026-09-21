#!/usr/bin/env python3
"""
Скрипт для очистки дубликатов отложенных кодов
Оставляет только самый новый код для каждого username

Запуск: python cleanup_pending_codes.py
"""

import asyncio
from sqlalchemy import select, and_
from database import async_session_maker
from models import AccessCode


async def cleanup_all_pending_codes():
    """Очистить все дубликаты отложенных кодов"""
    
    async with async_session_maker() as session:
        print("=" * 60)
        print("ОЧИСТКА ДУБЛИКАТОВ ОТЛОЖЕННЫХ КОДОВ")
        print("=" * 60)
        
        # Находим все отложенные коды
        result = await session.execute(
            select(AccessCode).where(
                and_(
                    AccessCode.code.like("PENDING_%"),
                    AccessCode.is_active == True,
                    AccessCode.activated_by.is_(None)
                )
            ).order_by(AccessCode.code)
        )
        
        all_codes = result.scalars().all()
        
        if not all_codes:
            print("\n✅ Отложенных кодов нет")
            return
        
        print(f"\n📋 Найдено отложенных кодов: {len(all_codes)}")
        
        # Группируем по username
        codes_by_username = {}
        for code in all_codes:
            # Извлекаем username из кода PENDING_username_timestamp
            parts = code.code.split('_')
            if len(parts) >= 2:
                username = parts[1]
                if username not in codes_by_username:
                    codes_by_username[username] = []
                codes_by_username[username].append(code)
        
        print(f"📊 Уникальных username: {len(codes_by_username)}")
        
        # Проверяем дубликаты
        total_deleted = 0
        
        for username, codes in codes_by_username.items():
            if len(codes) > 1:
                print(f"\n⚠️ Найдено {len(codes)} кодов для @{username}")
                
                # Сортируем по дате создания (новые первые)
                codes.sort(key=lambda c: c.created_at, reverse=True)
                
                # Показываем все коды
                for i, code in enumerate(codes):
                    marker = "✅ ОСТАВИТЬ" if i == 0 else "❌ УДАЛИТЬ"
                    print(f"   [{marker}] {code.code}")
                    print(f"      Создан: {code.created_at}")
                    print(f"      Дней: {code.duration_days}")
                
                # Удаляем старые (все кроме первого)
                codes_to_delete = codes[1:]
                for code in codes_to_delete:
                    await session.delete(code)
                    total_deleted += 1
            else:
                print(f"✅ @{username}: 1 код (дубликатов нет)")
        
        if total_deleted > 0:
            await session.commit()
            print(f"\n🗑️ Удалено дубликатов: {total_deleted}")
            print(f"✅ Оставлено актуальных: {len(codes_by_username)}")
        else:
            print(f"\n✅ Дубликатов не найдено")
        
        print("\n" + "=" * 60)
        print("ОЧИСТКА ЗАВЕРШЕНА")
        print("=" * 60)


async def show_current_pending_codes():
    """Показать все текущие отложенные коды"""
    
    async with async_session_maker() as session:
        print("\n" + "=" * 60)
        print("ТЕКУЩИЕ ОТЛОЖЕННЫЕ КОДЫ")
        print("=" * 60)
        
        result = await session.execute(
            select(AccessCode).where(
                and_(
                    AccessCode.code.like("PENDING_%"),
                    AccessCode.is_active == True,
                    AccessCode.activated_by.is_(None)
                )
            ).order_by(AccessCode.created_at.desc())
        )
        
        codes = result.scalars().all()
        
        if not codes:
            print("\n✅ Отложенных кодов нет")
        else:
            print(f"\n📋 Всего: {len(codes)}")
            print()
            
            for code in codes:
                # Извлекаем username
                parts = code.code.split('_')
                username = parts[1] if len(parts) >= 2 else "unknown"
                
                print(f"👤 @{username}")
                print(f"   Код: {code.code}")
                print(f"   Дней: {code.duration_days}")
                print(f"   Создан: {code.created_at.strftime('%d.%m.%Y %H:%M:%S')}")
                print()
        
        print("=" * 60)


async def main():
    """Главная функция"""
    
    # Показываем текущее состояние
    await show_current_pending_codes()
    
    # Спрашиваем подтверждение
    print("\n⚠️ Будут удалены старые дубликаты отложенных кодов.")
    print("   Для каждого username останется только самый новый код.")
    
    response = input("\n❓ Продолжить? (yes/no): ").strip().lower()
    
    if response in ['yes', 'y', 'да', 'д']:
        print()
        await cleanup_all_pending_codes()
        
        # Показываем результат
        await show_current_pending_codes()
    else:
        print("\n❌ Отменено")


if __name__ == "__main__":
    asyncio.run(main())
