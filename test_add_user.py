#!/usr/bin/env python3
"""
Тестовый скрипт для проверки добавления пользователей
Запуск: python test_add_user.py
"""

import asyncio
import sys
from sqlalchemy import select
from database import async_session_maker
from services import AccessService, UserService
from models import AccessCode, User


async def test_add_existing_user():
    """Тест: Добавление существующего пользователя"""
    print("\n" + "="*60)
    print("ТЕСТ 1: Добавление СУЩЕСТВУЮЩЕГО пользователя")
    print("="*60)
    
    async with async_session_maker() as session:
        # Ищем любого пользователя с username
        result = await session.execute(
            select(User).where(User.username.isnot(None)).limit(1)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            print("❌ В БД нет пользователей с username")
            print("   Сначала запустите бота и нажмите /start с любого аккаунта")
            return False
        
        username = user.username
        telegram_id = user.telegram_id
        
        print(f"✅ Найден пользователь:")
        print(f"   Username: @{username}")
        print(f"   Telegram ID: {telegram_id}")
        print(f"   Имя: {user.full_name}")
        
        # Пробуем выдать доступ
        print(f"\n🔧 Выдаём доступ на 30 дней...")
        
        success, msg, found_telegram_id = await AccessService.give_access_by_username(
            session,
            username,
            30,
            123456789  # Фейковый admin ID
        )
        
        if success:
            print(f"✅ УСПЕХ: {msg}")
            print(f"   Telegram ID: {found_telegram_id}")
            await session.commit()
            
            # Проверяем что код создался
            code_result = await session.execute(
                select(AccessCode).where(
                    AccessCode.activated_by == user.id,
                    AccessCode.is_active == False
                ).order_by(AccessCode.created_at.desc()).limit(1)
            )
            code = code_result.scalar_one_or_none()
            
            if code:
                print(f"\n📋 Код доступа создан:")
                print(f"   Code: {code.code}")
                print(f"   Expires: {code.expires_at}")
                print(f"   Days left: {code.days_left}")
            
            return True
        else:
            print(f"❌ ОШИБКА: {msg}")
            return False


async def test_add_pending_user():
    """Тест: Добавление несуществующего пользователя (отложенный доступ)"""
    print("\n" + "="*60)
    print("ТЕСТ 2: Отложенный доступ для НОВОГО пользователя")
    print("="*60)
    
    test_username = f"test_new_user_{int(asyncio.get_event_loop().time())}"
    
    async with async_session_maker() as session:
        print(f"🔧 Создаём отложенный доступ для @{test_username}")
        print(f"   Период: 60 дней")
        
        success, msg, found_telegram_id = await AccessService.give_access_by_username(
            session,
            test_username,
            60,
            123456789  # Фейковый admin ID
        )
        
        if success:
            print(f"✅ УСПЕХ: {msg}")
            await session.commit()
            
            # Проверяем что код создался
            code_result = await session.execute(
                select(AccessCode).where(
                    AccessCode.code.like(f"PENDING_{test_username.lower()}_%"),
                    AccessCode.is_active == True
                )
            )
            code = code_result.scalar_one_or_none()
            
            if code:
                print(f"\n📋 Отложенный код создан:")
                print(f"   Code: {code.code}")
                print(f"   Duration: {code.duration_days} дней")
                print(f"   Activated by: {code.activated_by} (должно быть None)")
                print(f"   Is active: {code.is_active} (должно быть True)")
                
                print(f"\n💡 Когда пользователь @{test_username} запустит /start:")
                print(f"   1. Создастся User с username = '{test_username}'")
                print(f"   2. Найдется этот код")
                print(f"   3. Код активируется автоматически")
                print(f"   4. expires_at = сейчас + 60 дней")
                
                return True
            else:
                print(f"❌ Код НЕ создался в БД!")
                return False
        else:
            print(f"❌ ОШИБКА: {msg}")
            return False


async def test_pending_activation():
    """Тест: Активация отложенного доступа"""
    print("\n" + "="*60)
    print("ТЕСТ 3: Активация отложенного доступа")
    print("="*60)
    
    async with async_session_maker() as session:
        # Ищем любой отложенный код
        result = await session.execute(
            select(AccessCode).where(
                AccessCode.is_active == True,
                AccessCode.activated_by.is_(None),
                AccessCode.code.like("PENDING_%")
            ).limit(1)
        )
        pending_code = result.scalar_one_or_none()
        
        if not pending_code:
            print("❌ Нет отложенных кодов для теста")
            print("   Сначала запустите ТЕСТ 2")
            return False
        
        # Извлекаем username из кода
        code_parts = pending_code.code.split('_')
        if len(code_parts) >= 2:
            username = code_parts[1]
        else:
            print(f"❌ Не удалось извлечь username из кода: {pending_code.code}")
            return False
        
        print(f"✅ Найден отложенный код:")
        print(f"   Code: {pending_code.code}")
        print(f"   Username: @{username}")
        print(f"   Duration: {pending_code.duration_days} дней")
        
        # Создаём пользователя (эмулируем /start)
        print(f"\n🔧 Эмулируем /start от пользователя @{username}")
        
        # Проверяем что пользователя нет
        existing_user = await UserService.get_user_by_username(session, username)
        if existing_user:
            print(f"⚠️ Пользователь @{username} уже существует (ID: {existing_user.id})")
            user = existing_user
        else:
            print(f"✅ Создаём пользователя...")
            # Создаём фейкового пользователя
            user = await UserService.create_user(
                session,
                telegram_id=999999999,  # Фейковый ID
                username=username,
                first_name="Test",
                last_name="User"
            )
            await session.flush()
            print(f"   User ID: {user.id}")
            print(f"   Telegram ID: {user.telegram_id}")
        
        # Пробуем активировать отложенный доступ
        print(f"\n🔧 Активируем отложенный доступ...")
        
        activated = await AccessService.activate_pending_access_for_user(
            session,
            user.id,
            username
        )
        
        if activated:
            print(f"✅ УСПЕХ: Отложенный доступ активирован!")
            await session.commit()
            
            # Проверяем что код обновился
            await session.refresh(pending_code)
            print(f"\n📋 Код после активации:")
            print(f"   Activated by: {pending_code.activated_by} (должно быть {user.id})")
            print(f"   Activated at: {pending_code.activated_at}")
            print(f"   Expires at: {pending_code.expires_at}")
            print(f"   Is active: {pending_code.is_active} (должно быть False)")
            print(f"   Days left: {pending_code.days_left}")
            
            return True
        else:
            print(f"❌ Отложенный доступ НЕ активировался")
            print(f"   Возможные причины:")
            print(f"   - Username не совпадает")
            print(f"   - Код уже активирован")
            print(f"   - Ошибка в функции activate_pending_access_for_user()")
            return False


async def main():
    """Главная функция"""
    print("\n" + "="*70)
    print(" ТЕСТИРОВАНИЕ СИСТЕМЫ ДОБАВЛЕНИЯ ПОЛЬЗОВАТЕЛЕЙ")
    print("="*70)
    
    try:
        # Тест 1: Существующий пользователь
        result1 = await test_add_existing_user()
        
        # Тест 2: Отложенный доступ
        result2 = await test_add_pending_user()
        
        # Тест 3: Активация отложенного доступа
        result3 = await test_pending_activation()
        
        # Итоги
        print("\n" + "="*70)
        print(" ИТОГИ ТЕСТИРОВАНИЯ")
        print("="*70)
        print(f"Тест 1 (Существующий пользователь): {'✅ PASSED' if result1 else '❌ FAILED'}")
        print(f"Тест 2 (Отложенный доступ):         {'✅ PASSED' if result2 else '❌ FAILED'}")
        print(f"Тест 3 (Активация отложенного):     {'✅ PASSED' if result3 else '❌ FAILED'}")
        print("="*70)
        
        if result1 and result2 and result3:
            print("\n🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ! Система добавления пользователей работает!")
            return 0
        else:
            print("\n⚠️ НЕКОТОРЫЕ ТЕСТЫ НЕ ПРОШЛИ. Проверьте логи выше.")
            return 1
    
    except Exception as e:
        print(f"\n❌ КРИТИЧЕСКАЯ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
