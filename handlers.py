import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, constants
from telegram.ext import ContextTypes, ConversationHandler
import database as db

logger = logging.getLogger(__name__)

# States for ConversationHandler (if needed, though we manage state in DB)
# We'll primarily use db.get_user_state for simpler logic flow here

# --- Menu Keyboard ---
def get_main_menu_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Generates the main menu keyboard based on current user config."""
    base_group = db.get_base_group(user_id)
    dest_groups = db.get_destination_groups(user_id)

    keyboard = []
    if base_group:
        base_group_id, base_group_name = base_group
        keyboard.append([InlineKeyboardButton(f"🔄 Cambiar Grupo Base ({base_group_name})", callback_data='set_base')])
        keyboard.append([InlineKeyboardButton("❌ Limpiar Grupo Base", callback_data='clear_base')])
        # Only allow adding destinations if base is set
        keyboard.append([InlineKeyboardButton("➕ Añadir Grupo Destino", callback_data='add_dest')])
        if dest_groups:
            keyboard.append([InlineKeyboardButton(f"🗑️ Ver/Borrar Grupos Destino ({len(dest_groups)})", callback_data='view_dest')])
    else:
        keyboard.append([InlineKeyboardButton("🎯 Establecer Grupo Base", callback_data='set_base')])

    keyboard.append([InlineKeyboardButton("ℹ️ Ver Configuración Actual", callback_data='view_config')])
    keyboard.append([InlineKeyboardButton("🔄 Refrescar Menú", callback_data='refresh_menu')])

    return InlineKeyboardMarkup(keyboard)

def get_view_dest_keyboard(user_id: int) -> InlineKeyboardMarkup | None:
    """Generates keyboard for viewing/deleting destination groups."""
    dest_groups = db.get_destination_groups(user_id)
    if not dest_groups:
        return None

    keyboard = []
    for group_id, group_name in dest_groups:
        # Using f-string for callback data; ensure parsing handles it
        keyboard.append([InlineKeyboardButton(f"❌ Borrar: {group_name}", callback_data=f'delete_dest_{group_id}')])

    keyboard.append([InlineKeyboardButton("🔙 Volver al Menú Principal", callback_data='main_menu')])
    return InlineKeyboardMarkup(keyboard)


# --- Command Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the /start command, displays the main menu and instructions."""
    user = update.effective_user
    user_id = user.id
    logger.info(f"User {user_id} ({user.username}) started the bot.")

    # Ensure user exists in DB, set state to idle if new
    if db.get_user_state(user_id) is None:
         db.set_user_state(user_id, 'idle')

    welcome_message = (
        f"¡Hola {user.mention_html()}! 👋\n\n"
        f"Soy tu asistente para reenviar mensajes entre grupos de Telegram.\n\n"
        f"**¿Cómo funciona?**\n"
        f"1. **Añádeme** a los grupos que quieres usar (el grupo 'base' de donde leeré los mensajes y los grupos 'destino' a donde los enviaré).\n"
        f"2. Usa el menú de abajo para **configurar** cuál es tu grupo base y cuáles son tus grupos destino.\n"
        f"   - Para configurar un grupo, deberás **reenviarme un mensaje cualquiera** de ese grupo.\n"
        f"3. Una vez configurado, reenviaré automáticamente los mensajes del grupo base a los grupos destino.\n\n"
        f"**Importante:**\n"
        f"- Solo puedo leer/reenviar mensajes si estoy en los grupos y tengo permisos.\n"
        f"- Cada usuario tiene su propia configuración independiente.\n"
        f"- No se permite que dos configuraciones distintas usen el mismo grupo base para reenviar al *mismo* grupo destino.\n\n"
        f"Usa los botones de abajo para empezar:"
    )

    await update.message.reply_html(
        text=welcome_message,
        reply_markup=get_main_menu_keyboard(user_id),
        disable_web_page_preview=True
    )

# --- Callback Query Handlers ---
async def button_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles all button presses from inline keyboards."""
    query = update.callback_query
    await query.answer() # Acknowledge the button press
    user_id = query.from_user.id
    callback_data = query.data

    logger.debug(f"Received callback query: {callback_data} from user {user_id}")

    # --- Main Menu Actions ---
    if callback_data == 'main_menu':
        await query.edit_message_text(
            text="Menú Principal:",
            reply_markup=get_main_menu_keyboard(user_id),
            parse_mode=constants.ParseMode.HTML
        )
    elif callback_data == 'refresh_menu':
         await query.edit_message_reply_markup(reply_markup=get_main_menu_keyboard(user_id))

    elif callback_data == 'set_base':
        db.set_user_state(user_id, 'awaiting_base_forward')
        await query.edit_message_text(
            text="Ok, por favor, **reenvíame un mensaje cualquiera** del grupo que quieres usar como **grupo base**. Asegúrate de que estoy en ese grupo.",
            parse_mode=constants.ParseMode.HTML
        )

    elif callback_data == 'clear_base':
        db.clear_base_group(user_id)
        await query.edit_message_text(
            text="✅ Grupo base eliminado. Ya no se reenviarán mensajes desde ese grupo.\n\nMenú Principal:",
            reply_markup=get_main_menu_keyboard(user_id),
            parse_mode=constants.ParseMode.HTML
        )

    elif callback_data == 'add_dest':
        base_group = db.get_base_group(user_id)
        if not base_group:
             await query.edit_message_text(
                text="⚠️ Primero debes establecer un grupo base antes de añadir destinos.\n\nMenú Principal:",
                reply_markup=get_main_menu_keyboard(user_id),
                parse_mode=constants.ParseMode.HTML
             )
             return
        db.set_user_state(user_id, 'awaiting_dest_forward')
        await query.edit_message_text(
            text="Ok, por favor, **reenvíame un mensaje cualquiera** del grupo que quieres añadir como **destino**. Asegúrate de que estoy en ese grupo.",
            parse_mode=constants.ParseMode.HTML
        )

    elif callback_data == 'view_dest':
        keyboard = get_view_dest_keyboard(user_id)
        dest_groups = db.get_destination_groups(user_id) # Fetch again for count
        if keyboard:
             await query.edit_message_text(
                 text=f"Tus grupos destino ({len(dest_groups)}):\n(Pulsa sobre un grupo para eliminarlo)",
                 reply_markup=keyboard,
                 parse_mode=constants.ParseMode.HTML
             )
        else:
            await query.edit_message_text(
                text="No tienes grupos destino configurados.\n\nMenú Principal:",
                reply_markup=get_main_menu_keyboard(user_id),
                parse_mode=constants.ParseMode.HTML
            )

    elif callback_data.startswith('delete_dest_'):
        try:
            group_id_to_delete = int(callback_data.split('_')[2])
            removed = db.remove_destination_group(user_id, group_id_to_delete)
            if removed:
                await context.bot.send_message(chat_id=user_id, text=f"✅ Grupo destino (ID: {group_id_to_delete}) eliminado.")
                 # Refresh the delete view or go back to main menu
                keyboard = get_view_dest_keyboard(user_id)
                dest_groups = db.get_destination_groups(user_id) # Fetch again for count
                if keyboard:
                    await query.edit_message_text(
                        text=f"Tus grupos destino ({len(dest_groups)}):\n(Pulsa sobre un grupo para eliminarlo)",
                        reply_markup=keyboard,
                        parse_mode=constants.ParseMode.HTML
                    )
                else:
                     await query.edit_message_text(
                         text="Todos los grupos destino eliminados.\n\nMenú Principal:",
                         reply_markup=get_main_menu_keyboard(user_id),
                         parse_mode=constants.ParseMode.HTML
                     )
            else:
                 await context.bot.send_message(chat_id=user_id, text=f"⚠️ No se pudo eliminar el grupo destino (ID: {group_id_to_delete}), quizás ya no existía.")
                 # Refresh view just in case
                 keyboard = get_view_dest_keyboard(user_id)
                 dest_groups = db.get_destination_groups(user_id) # Fetch again for count
                 await query.edit_message_text(
                     text=f"Tus grupos destino ({len(dest_groups)}):\n(Pulsa sobre un grupo para eliminarlo)",
                     reply_markup=keyboard,
                     parse_mode=constants.ParseMode.HTML
                 )

        except (IndexError, ValueError):
            logger.warning(f"Invalid callback data for delete_dest: {callback_data}")
            await context.bot.send_message(chat_id=user_id, text="Error procesando la solicitud.")
            # Go back to main menu on error
            await query.edit_message_text(
                text="Menú Principal:",
                reply_markup=get_main_menu_keyboard(user_id),
                parse_mode=constants.ParseMode.HTML
            )


    elif callback_data == 'view_config':
        base_group = db.get_base_group(user_id)
        dest_groups = db.get_destination_groups(user_id)

        message = "⚙️ **Tu Configuración Actual** ⚙️\n\n"
        if base_group:
            base_id, base_name = base_group
            message += f"*️⃣ **Grupo Base:** {base_name} (ID: `{base_id}`)\n"
        else:
            message += "*️⃣ **Grupo Base:** ¡No establecido!\n"

        message += f"\n➡️ **Grupos Destino ({len(dest_groups)}):**\n"
        if dest_groups:
            for i, (dest_id, dest_name) in enumerate(dest_groups):
                message += f"  {i+1}. {dest_name} (ID: `{dest_id}`)\n"
        else:
            message += "  ¡Ninguno! No se reenviarán mensajes.\n"

        await query.edit_message_text(
            text=message,
            reply_markup=get_main_menu_keyboard(user_id), # Show main menu again
            parse_mode=constants.ParseMode.MARKDOWN_V2
        )


# --- Message Handlers ---
async def handle_forwarded_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles forwarded messages in private chat to set groups."""
    user = update.effective_user
    message = update.effective_message
    chat = update.effective_chat

    if chat.type != constants.ChatType.PRIVATE:
        return # Only process forwards in private chat with the bot

    if not message.forward_from_chat:
        # This handles cases where the forward is from a user who hides their account
        # or from a channel where the original sender isn't linked.
        # We need the chat ID, so if it's missing, we can't proceed.
         if message.forward_origin and message.forward_origin.type == 'channel':
             # Forwards from channels might have the chat info here
             forwarded_chat = message.forward_origin.chat
         elif message.forward_sender_name: # Last resort, maybe a hidden user forward
            await message.reply_text(
                "No puedo identificar el grupo original porque el usuario ha ocultado su cuenta o la información no está disponible. Por favor, reenvía un mensaje de un usuario visible o directamente del grupo/canal.",
                reply_markup=get_main_menu_keyboard(user.id)
            )
            db.set_user_state(user.id, 'idle')
            return
         else:
            await message.reply_text(
                "No puedo identificar el grupo de origen de este mensaje reenviado. Intenta reenviar un mensaje diferente.",
                 reply_markup=get_main_menu_keyboard(user.id)
            )
            db.set_user_state(user.id, 'idle')
            return

    else:
        forwarded_chat = message.forward_from_chat


    if not forwarded_chat or forwarded_chat.type not in [constants.ChatType.GROUP, constants.ChatType.SUPERGROUP, constants.ChatType.CHANNEL]:
        await message.reply_text(
            "Por favor, reenvía un mensaje desde un **grupo** o **canal**.",
             reply_markup=get_main_menu_keyboard(user.id)
        )
        db.set_user_state(user.id, 'idle')
        return

    group_id = forwarded_chat.id
    group_name = forwarded_chat.title or f"Grupo/Canal sin nombre (ID: {group_id})"
    user_id = user.id
    current_state = db.get_user_state(user_id)

    logger.info(f"Received forwarded message from chat {group_id} ({group_name}) for user {user_id} in state {current_state}")

    # Check bot membership (best effort)
    try:
        bot_member = await context.bot.get_chat_member(group_id, context.bot.id)
        if bot_member.status in [constants.ChatMemberStatus.LEFT, constants.ChatMemberStatus.KICKED]:
            raise Exception("Bot not member") # Treat as not being a member
        logger.info(f"Bot is a member of group {group_id} with status {bot_member.status}")
    except Exception as e:
        logger.warning(f"Could not verify bot membership in {group_id} ({group_name}): {e}")
        await message.reply_text(
             f"⚠️ **¡Atención!** No he podido confirmar si estoy en el grupo '{group_name}'. "
             f"Asegúrate de que he sido añadido correctamente.\n\n"
             f"Continuaré con la configuración, pero podría fallar si no estoy en el grupo.",
            parse_mode=constants.ParseMode.HTML
        )
        # Continue with configuration despite warning

    if current_state == 'awaiting_base_forward':
        try:
            db.set_base_group(user_id, group_id, group_name)
            await message.reply_text(
                f"✅ ¡Estupendo! Has establecido '{group_name}' como tu **grupo base**.\n\n"
                f"Ahora puedes añadir grupos destino desde el menú.",
                reply_markup=get_main_menu_keyboard(user_id),
                parse_mode=constants.ParseMode.HTML
            )
        except ValueError as e: # Handles specific errors from db layer
             await message.reply_text(f"⚠️ Error al establecer grupo base: {e}", reply_markup=get_main_menu_keyboard(user.id))
        except Exception as e:
            logger.error(f"Unexpected error setting base group for {user_id}: {e}")
            await message.reply_text("❌ Ocurrió un error inesperado al guardar el grupo base.", reply_markup=get_main_menu_keyboard(user_id))
        finally:
             db.set_user_state(user_id, 'idle') # Always reset state


    elif current_state == 'awaiting_dest_forward':
        base_group = db.get_base_group(user_id)
        if not base_group: # Should not happen if state is correct, but check anyway
             await message.reply_text("⚠️ Error interno: No hay grupo base configurado. Por favor, vuelve a empezar.", reply_markup=get_main_menu_keyboard(user_id))
             db.set_user_state(user_id, 'idle')
             return

        base_group_id, _ = base_group

        # Check for base == destination conflict for THIS user
        if group_id == base_group_id:
            await message.reply_text(
                 f"⚠️ No puedes añadir el grupo base ('{group_name}') como grupo destino.",
                reply_markup=get_main_menu_keyboard(user_id)
            )
            db.set_user_state(user_id, 'idle')
            return

        # Check for conflict: ANY user forwarding from this user's base_group_id TO the new group_id
        if db.check_destination_conflict(base_group_id, group_id):
            await message.reply_text(
                f"⚠️ ¡Conflicto! Otro usuario ya está reenviando mensajes desde tu grupo base ('{base_group[1]}') hacia este grupo destino ('{group_name}'). No se permite esta configuración duplicada.",
                reply_markup=get_main_menu_keyboard(user_id)
            )
            db.set_user_state(user_id, 'idle')
            return

        try:
            db.add_destination_group(user_id, group_id, group_name)
            dest_count = len(db.get_destination_groups(user_id))
            await message.reply_text(
                f"✅ ¡Grupo destino '{group_name}' añadido! "
                f"Ahora tienes {dest_count} {'grupo destino' if dest_count == 1 else 'grupos destino'}.\n\n"
                f"Puedes añadir más o volver al menú.",
                reply_markup=get_main_menu_keyboard(user_id), # Back to main menu
                parse_mode=constants.ParseMode.HTML
            )
        except ValueError as e: # Handles specific errors from db layer (e.g., duplicate)
            await message.reply_text(f"⚠️ Error al añadir grupo destino: {e}", reply_markup=get_main_menu_keyboard(user_id))
        except Exception as e:
            logger.error(f"Unexpected error adding destination group for {user_id}: {e}")
            await message.reply_text("❌ Ocurrió un error inesperado al guardar el grupo destino.", reply_markup=get_main_menu_keyboard(user_id))
        finally:
             db.set_user_state(user_id, 'idle') # Always reset state

    else:
        # Received a forwarded message but wasn't expecting one
        await message.reply_text(
            "Recibí un mensaje reenviado, pero no estaba esperando uno ahora mismo. Si querías configurar un grupo, usa los botones del menú primero.",
            reply_markup=get_main_menu_keyboard(user.id)
        )


async def handle_group_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles messages received in any group/channel the bot is in."""
    message = update.effective_message
    chat = update.effective_chat

    if not message or not chat:
        return # Ignore updates without message/chat

    # Ignore messages from other bots? (Optional, usually good)
    if message.from_user.is_bot:
        return

    # Ignore commands in groups (we handle them in private chat)
    if message.text and message.text.startswith('/'):
        return

    # --- Forwarding Logic ---
    current_chat_id = chat.id
    # Load all active forwarding rules (cache this in context.bot_data if performance becomes an issue)
    # For simplicity now, we query DB on each message. DB access is fast with indexes.
    all_configs = db.get_all_forwarding_configs()

    if current_chat_id in all_configs:
        destination_ids = all_configs[current_chat_id]
        if not destination_ids:
            logger.debug(f"Message received in base group {current_chat_id}, but no destinations configured.")
            return

        logger.info(f"Message received in configured base group {current_chat_id}. Forwarding to {len(destination_ids)} destinations: {destination_ids}")

        successful_forwards = 0
        failed_forwards = 0

        for dest_id in destination_ids:
            try:
                # Use forward_message for cleaner attribution
                await context.bot.forward_message(
                    chat_id=dest_id,
                    from_chat_id=current_chat_id,
                    message_id=message.message_id
                )
                # Alternative: Copy message (less attribution, might bypass some restrictions)
                # await context.bot.copy_message(
                #     chat_id=dest_id,
                #     from_chat_id=current_chat_id,
                #     message_id=message.message_id
                # )
                successful_forwards += 1
                # Optional: Short delay between forwards if rate limits are hit
                # await asyncio.sleep(0.1)
            except Exception as e:
                failed_forwards += 1
                logger.error(f"Failed to forward message {message.message_id} from {current_chat_id} to {dest_id}: {e}")
                # TODO: Consider notifying the user who configured this rule if forwarding fails repeatedly?
                # This could involve looking up which user(s) configured this base->dest link.
                # For now, just log the error.

        if failed_forwards > 0:
            logger.warning(f"Forwarding completed for message {message.message_id} from {current_chat_id}. Success: {successful_forwards}, Failed: {failed_forwards}")

    # else: Message is not from a configured base group, ignore.

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log Errors caused by Updates."""
    logger.error(f"Update {update} caused error {context.error}", exc_info=context.error)
    # Optionally, inform user about the error if it happened during interaction
    if isinstance(update, Update) and update.effective_user:
        user_id = update.effective_user.id
        try:
             await context.bot.send_message(
                 chat_id=user_id,
                 text="Ups! Algo salió mal procesando tu solicitud. Lo he registrado. Intenta de nuevo o contacta al administrador si persiste."
            )
             # Try showing the main menu again
             await context.bot.send_message(
                 chat_id=user_id,
                 text="Menú Principal:",
                 reply_markup=get_main_menu_keyboard(user_id)
             )
             # Reset state just in case
             db.set_user_state(user_id, 'idle')
        except Exception as e:
             logger.error(f"Failed to send error message to user {user_id}: {e}") 